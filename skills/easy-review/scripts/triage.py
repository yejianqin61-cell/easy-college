#!/usr/bin/env python
"""easy-learning -- page triage for PDF courseware.

One row per page: extractable text, image coverage, trap signatures, duplicate ratio.
Writes <out>/ledger.json, <out>/ledger.md and <out>/pages/pNN.png.

Usage:
    python triage.py INPUT.pdf [INPUT2.pdf ...] [--out DIR] [--dpi 150] [--no-render]

HTML courseware is triaged by scripts/triage-html.py, which writes the same ledger shape, so
steps 2-7 read either format identically. Both merge their entry into <out>/sources.json.

Exit codes: 0 ok | 1 missing dependency | 2 input could not be read
"""

import argparse
import collections
import itertools
import json
import os
import re
import statistics
import sys

try:
    import pymupdf
except ImportError:
    sys.stderr.write(
        "pymupdf is required for PDF triage. Install it with:\n"
        "    python -m pip install --quiet pymupdf\n"
    )
    sys.exit(1)

# Code-point ranges whose presence in a Latin page indicates a math font with no ToUnicode map.
GARBLE_RANGES = ((0x0600, 0x0DFF), (0xE000, 0xF8FF), (0xFB50, 0xFEFF))

RASTER_EXTRA_MIN = 0.08    # image coverage above the document's background baseline
THIN_TEXT_CHARS = 120      # below this a page needs a human look at the render
FULL_BLEED_MEDIAN = 0.50   # median coverage this high means every page is one background image
OVERLAP_MIN = 0.45         # two spans overlapping this much are a hidden-text candidate
DUP_MIN = 0.85             # token-set overlap with the previous page
NOISE_PAGE_SHARE = 0.90    # a short token on this share of pages is master noise


def garbled(text):
    """Distinct garbled code points in `text`."""
    out = set()
    for ch in text:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in GARBLE_RANGES):
            out.add(ch)
    return "".join(sorted(out))


def spans(page):
    """(text, rect, char_rects) for every non-empty span."""
    out = []
    for block in page.get_text("rawdict")["blocks"]:
        if block.get("type"):
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = "".join(c["c"] for c in span["chars"]).strip()
                if not text:
                    continue
                out.append((text, pymupdf.Rect(span["bbox"]),
                            [pymupdf.Rect(c["bbox"]) for c in span["chars"] if c["c"].strip()]))
    return out


def overlap_ratio(a, b):
    inter = a & b
    if inter.is_empty:
        return 0.0
    smaller = min(a.get_area(), b.get_area())
    return inter.get_area() / smaller if smaller else 0.0


def hidden_pairs(page):
    """Span pairs that overlap enough that one may be painted over the other.

    A span that sits entirely inside another span's whitespace gaps is an inline variable
    ("a physical quantity f is a function of"), not hidden text, and is not reported.
    """
    found = []
    for (t1, r1, c1), (t2, r2, c2) in itertools.combinations(spans(page), 2):
        if t1 == t2 and r1 == r2:
            continue
        ratio = overlap_ratio(r1, r2)
        if ratio <= OVERLAP_MIN:
            continue
        if r1.get_area() >= r2.get_area():
            long_chars, short_rect = c1, r2
        else:
            long_chars, short_rect = c2, r1
        if long_chars and not any(ch.intersects(short_rect) for ch in long_chars):
            continue                       # inline variable in a gap
        found.append({"a": t1, "b": t2, "ratio": round(ratio, 2)})
    return found


def raster_coverage(page):
    area = page.rect.get_area()
    covers = [rect.get_area() / area
              for img in page.get_images(full=True)
              for rect in page.get_image_rects(img[0])]
    return round(max(covers), 3) if covers else 0.0


def token_set(text):
    return set(re.sub(r"\s+", " ", text).strip().split())


def triage(path, out_dir, dpi, render):
    doc = pymupdf.open(path)
    name = os.path.splitext(os.path.basename(path))[0]

    pages = []
    for number, page in enumerate(doc, 1):
        text = page.get_text("text")
        pages.append({"page": number, "page_obj": page, "text": text,
                      "coverage": raster_coverage(page)})

    # Baseline: the deck's own background. A full-bleed deck makes coverage useless as a signal,
    # so it is reported once, at document level, instead of mislabelled on every page.
    baseline = statistics.median(p["coverage"] for p in pages) if pages else 0.0
    full_bleed = baseline >= FULL_BLEED_MEDIAN

    rows = []
    prev_tokens = None
    for entry in pages:
        page, text = entry["page_obj"], entry["text"]
        tokens = token_set(text)
        dup = 0.0
        if prev_tokens:
            union = len(tokens | prev_tokens)
            dup = len(tokens & prev_tokens) / union if union else 0.0
        prev_tokens = tokens

        chars = len(text.strip())
        traps = []
        pairs = hidden_pairs(page)
        if pairs:
            traps.append("ghost-text")
        garbled_chars = garbled(text)
        if garbled_chars:
            traps.append("garbled-math")
        if full_bleed:
            if chars < THIN_TEXT_CHARS:
                traps.append("empty-text" if chars == 0 else "thin-text")
        elif entry["coverage"] - baseline >= RASTER_EXTRA_MIN and chars < THIN_TEXT_CHARS:
            traps.append("raster-only")
        if dup >= DUP_MIN:
            traps.append("duplicate")

        if "ghost-text" in traps:
            verdict = "needs-human"
        elif traps:
            verdict = "needs-vision"
        else:
            verdict = "readable"

        if render:
            page.get_pixmap(dpi=dpi).save(
                os.path.join(out_dir, "pages", f"{name}-p{entry['page']:02d}.png"))

        rows.append({"src": os.path.basename(path), "page": entry["page"], "chars": chars,
                     "raster": entry["coverage"], "traps": traps, "verdict": verdict,
                     "hidden": pairs[:5], "garbled": garbled_chars, "dup": round(dup, 2)})

    counts = collections.Counter()
    for p in pages:
        counts.update(set(re.findall(r"[^\s]{1,24}", p["text"])))
    threshold = max(2, int(len(rows) * NOISE_PAGE_SHARE))
    noise = sorted(t for t, c in counts.items() if c >= threshold and len(t) <= 24)

    return name, rows, noise, baseline, full_bleed


def write_ledger(out_dir, name, rows, noise, sources, baseline, full_bleed):
    os.makedirs(os.path.join(out_dir, "pages"), exist_ok=True)
    with open(os.path.join(out_dir, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump({"sources": sources, "master_noise": noise,
                   "background_baseline": baseline, "full_bleed": full_bleed, "pages": rows},
                  fh, ensure_ascii=False, indent=1)

    counts = collections.Counter(r["verdict"] for r in rows)
    trap_counts = collections.Counter(t for r in rows for t in r["traps"])
    lines = [f"# Page ledger — {name}", "",
             f"Pages **{len(rows)}** | readable {counts['readable']} | "
             f"needs-vision {counts['needs-vision']} | needs-human {counts['needs-human']}", ""]
    if full_bleed:
        lines += [f"> This deck is **full-bleed raster** (background baseline {baseline}): per-page "
                  "image coverage carries no signal, so every text-thin page is flagged `thin-text` "
                  "and sent to the vision pass.", ""]
    lines += ["| Trap | Pages |", "|---|---|"]
    lines += [f"| {t} | {c} |" for t, c in sorted(trap_counts.items())] or ["| — | 0 |"]
    if noise:
        lines += ["", "**Master noise** (repeats across pages; strip before analysis): "
                  + ", ".join(f"`{t}`" for t in noise)]
    lines += ["", "| Page | Chars | Raster | Traps | Verdict | Overlapping spans |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        hidden = "；".join(f"`{p['a']}`↔`{p['b']}` {p['ratio']}" for p in r["hidden"])
        lines.append("| {page} | {chars} | {raster} | {traps} | {verdict} | {hidden} |".format(
            page=r["page"], chars=r["chars"], raster=r["raster"],
            traps=",".join(r["traps"]) or "—", verdict=r["verdict"], hidden=hidden))
    with open(os.path.join(out_dir, "ledger.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return counts


def merge_sources(out_dir, entries):
    """Add this run's files to <out>/sources.json without dropping another format's rows.

    A session can hold a PDF and an HTML deck at once, so the two triage scripts must agree on
    this file rather than overwrite each other's.
    """
    path = os.path.join(out_dir, "sources.json")
    existing = []
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            existing = loaded if isinstance(loaded, list) else []
        except (ValueError, OSError):
            existing = []
    mine = {e["file"] for e in entries}
    merged = [e for e in existing if e.get("file") not in mine] + entries
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1)


def utf8_when_redirected():
    """Windows redirects stdout through the ANSI code page, so printing a CJK path raises
    UnicodeEncodeError and kills a triage that had already finished. A console keeps its own
    encoding; only a redirected stream is switched to UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main():
    utf8_when_redirected()
    ap = argparse.ArgumentParser(description="easy-learning PDF page triage")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", default="notes")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args()

    sources = []
    for path in args.inputs:
        if not os.path.isfile(path):
            sys.stderr.write(f"input not found: {path}\n")
            return 2
        name = os.path.splitext(os.path.basename(path))[0]
        out_dir = os.path.join(args.out, name)
        os.makedirs(os.path.join(out_dir, "pages"), exist_ok=True)
        try:
            name, rows, noise, baseline, full_bleed = triage(
                path, out_dir, args.dpi, not args.no_render)
        except Exception as exc:                       # unreadable / encrypted / corrupt
            sys.stderr.write(f"could not read {path}: {exc}\n")
            return 2
        counts = write_ledger(out_dir, name, rows, noise, [os.path.abspath(path)],
                              baseline, full_bleed)
        sources.append({"file": os.path.abspath(path), "format": "pdf", "pages": len(rows),
                        "unit": "page", "full_bleed": full_bleed, "verdicts": dict(counts),
                        "ledger": os.path.join(out_dir, "ledger.md")})
        print(f"{os.path.basename(path)}: {len(rows)} pages | "
              f"readable {counts['readable']} | needs-vision {counts['needs-vision']} | "
              f"needs-human {counts['needs-human']}"
              f"{' | full-bleed raster' if full_bleed else ''}")
        print(f"  ledger -> {os.path.join(out_dir, 'ledger.md')}")

    merge_sources(args.out, sources)
    return 0


if __name__ == "__main__":
    sys.exit(main())
