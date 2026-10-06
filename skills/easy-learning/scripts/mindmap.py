#!/usr/bin/env python
"""easy-learning -- build a mind map from a notes file's own headings.

The notes' structure is the single source of truth: `#` is the root, `##` a module,
`###` a knowledge point. Sections with no `###` child (appendices, errata) are skipped,
so the map shows knowledge structure rather than the document's furniture.

Usage:
    python mindmap.py NOTES.md [-o OUT.svg] [--insert] [--alt "<caption>"]
                                [--accent "#2f6fb5,#4a8a4a,..."]

Writes an SVG next to the notes. With --insert, also puts (or refreshes) the image
reference in the notes, just above the first module.

Exit codes: 0 ok | 2 nothing to draw
"""

import argparse
import os
import re
import sys

# --- typography -------------------------------------------------------------
FONT = "'Microsoft YaHei','PingFang SC','Hiragino Sans GB','Segoe UI',sans-serif"
ROOT_SIZE, MOD_SIZE, POINT_SIZE = 15.0, 13.0, 12.0
LINE_H = 1.42
PAD_X = 14.0
PAD_Y = 9.0
WRAP = {0: 236.0, 1: 208.0, 2: 302.0}

# Punctuation that must not be orphaned onto a line start, and openers that must not
# be left dangling at a line end. CJK closing marks and their ASCII counterparts.
NO_START = set("），,。、.；;：:％%！!？?）】」》…")
NO_END = set("（(【「《")

GAP_COL = 46.0        # horizontal gap between columns
GAP_POINT = 9.0       # vertical gap between knowledge points
GAP_BAND = 22.0       # vertical gap between module bands
MARGIN = 10.0

# A coherent set lifted from the notes stylesheet: deep blue first, then companions.
ACCENTS = ["#2f6fb5", "#4a8a4a", "#8a5a9e", "#b0712c", "#2c8a8a", "#a8517a"]
ROOT_FILL = "#1f3a5f"
INK = "#1a1a1a"
SOFT = "#5a6b7c"

THIN = set("iljI.,:;'|!()[]")

# Plain-text equivalents so a label reads as `T²–L` rather than `T^2–L` in SVG, which has no
# math typesetting of its own.
SUPER = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
         "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻"}
SUB = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
       "6": "₆", "7": "₇", "8": "₈", "9": "₉"}


def plain_math(text):
    """SVG text is not typeset, so `$1/r^2$` would print with its dollar signs and braces.

    This is a label, not the formula: strip the delimiters, keep the symbols. The notes carry the
    typeset version; the map only has to be recognisable at a glance.
    """
    if "$" not in text and "\\" not in text:
        return text
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    # Structures first, while their braces are still there: a fraction is a over b, and a vector
    # is its letter with a combining arrow.
    text = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", text)
    text = re.sub(r"\\(?:vec|overrightarrow)\{?([A-Za-z])\}?", "\\1\u20d7", text)
    text = re.sub(r"\\hat\{?([A-Za-z])\}?", "\\1\u0302", text)
    text = re.sub(r"\\(?:bar|overline)\{?([A-Za-z])\}?", "\\1\u0304", text)
    text = re.sub(r"\\(?:text|mathrm|operatorname)\{([^{}]*)\}", r"\1", text)
    for latex, glyph in (("\\pi", "π"), ("\\theta", "θ"), ("\\sigma", "σ"), ("\\Delta", "Δ"),
                         ("\\delta", "δ"), ("\\mu", "μ"), ("\\rho", "ρ"), ("\\lambda", "λ"),
                         ("\\epsilon", "ε"), ("\\varepsilon", "ε"), ("\\omega", "ω"),
                         ("\\Omega", "Ω"), ("\\phi", "φ"), ("\\infty", "∞"), ("\\partial", "∂"),
                         ("\\times", "×"), ("\\cdot", "·"), ("\\pm", "±"), ("\\mp", "∓"),
                         ("\\sqrt", "√"), ("\\le", "≤"), ("\\leq", "≤"), ("\\ge", "≥"),
                         ("\\geq", "≥"), ("\\approx", "≈"), ("\\neq", "≠"), ("\\to", "→"),
                         ("\\rightarrow", "→"), ("\\sum", "Σ"), ("\\int", "∫"), ("\\log", "log"),
                         ("\\quad", " "), ("\\,", " "), ("\\;", " "), ("\\!", ""), ("\\left", ""),
                         ("\\right", ""), ("\\", "")):
        text = text.replace(latex, glyph)
    text = re.sub(r"\^\{?([0-9+-]+)\}?", lambda m: SUPER.get(m.group(1), "^" + m.group(1)), text)
    text = re.sub(r"_\{?([0-9A-Za-z]+)\}?", lambda m: SUB.get(m.group(1), "_" + m.group(1)), text)
    return re.sub(r"\{([^{}]*)\}", r"\1", text)       # whatever braces are left held nothing


def link_target(path):
    """The map's file name as a markdown link target.

    Spaces, parentheses, `#` and `?` end a link destination early, so a notes file called
    `Lecture (2024).notes.md` produced a reference pandoc could not resolve. Percent-encoding
    those characters is what makes the link survive both markdown and pandoc's resource fetch;
    the rest of the name, including CJK, is left readable.
    """
    return os.path.basename(path).translate(
        str.maketrans({" ": "%20", "(": "%28", ")": "%29", "<": "%3C", ">": "%3E",
                       "#": "%23", "?": "%3F"}))


def shorten(text, limit=110):
    """A heading is a label, not a sentence: drop markdown emphasis and keep one clause."""
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\s*\{#[^}]*\}\s*$", "", text)     # a heading anchor is not part of the name
    text = plain_math(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        # Prefer cutting at a clause boundary so the label still reads as a label.
        head = text[:limit]
        for mark in ("（", "(", "：", ":", "；", ";", "，", ",", " "):
            cut = head.rfind(mark)
            if cut > limit * 0.5:
                return head[:cut].rstrip() + "…"
        return head.rstrip() + "…"
    return text


def text_width(text, size):
    """Approximate advance width; CJK and fullwidth forms count as one em."""
    total = 0.0
    for ch in text:
        if ord(ch) >= 0x2E80:
            total += 1.0
        elif ch in THIN:
            total += 0.30
        elif ch.isdigit() or ch.isupper():
            total += 0.58
        else:
            total += 0.52
    return total * size


def tokenize(text, size, max_width):
    """Split into wrappable tokens: a parenthetical group that fits stays atomic, CJK breaks
    per character, Latin breaks at spaces."""
    tokens, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch in "（(":
            # Full- and half-width brackets get mixed in the wild (`（Error Analysis)`),
            # so accept whichever closer comes first.
            closes = [p for p in (text.find(c, i) for c in "）)") if p != -1]
            j = min(closes) if closes else -1
            if j != -1 and text_width(text[i:j + 1], size) <= max_width * 1.15:
                tokens.append(text[i:j + 1])
                i = j + 1
                continue
        if ord(ch) >= 0x2E80:
            tokens.append(ch)
            i += 1
            continue
        j = i
        while j < len(text) and ord(text[j]) < 0x2E80 and not text[j].isspace():
            j += 1
        tokens.append(text[i:j])
        if j < len(text) and text[j] == " ":
            tokens.append(" ")
            j += 1
        i = j
    return tokens


def wrap(text, size, max_width):
    """Greedy wrap that keeps parenthetical groups whole and never orphans closing punctuation."""
    lines, current = [], ""
    for token in tokenize(text, size, max_width):
        if token == " " and not current:
            continue
        if not current or text_width(current + token, size) <= max_width:
            current += token
            continue
        lines.append(current.rstrip())
        current = "" if token == " " else token
    if current.strip():
        lines.append(current.rstrip())

    # Repair pass: keep closing marks off line starts, and openers off line ends.
    out = []
    for line in lines:
        while line and line[0] in NO_START and out:
            out[-1] += line[0]
            line = line[1:]
        if not line.strip():
            continue
        if len(line) > 1 and line[-1] in NO_END:
            out.append(line[:-1])
            out.append(line[-1])          # a lone opener, merged with what follows
        else:
            out.append(line)

    merged, i = [], 0
    while i < len(out):
        if len(out[i]) == 1 and out[i] in NO_END and i + 1 < len(out):
            merged.append(out[i] + out[i + 1])
            i += 2
        else:
            merged.append(out[i])
            i += 1
    return merged or [text]


class Node:
    def __init__(self, label, level):
        self.label = label
        self.level = level
        self.size = (ROOT_SIZE, MOD_SIZE, POINT_SIZE)[level]
        self.lines = wrap(label, self.size, WRAP[level])
        self.w = max(text_width(l, self.size) for l in self.lines) + 2 * PAD_X
        self.h = len(self.lines) * self.size * LINE_H + 2 * PAD_Y
        self.x = self.y = 0.0

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def right(self):
        return self.x + self.w


def parse(path):
    """Return (title, [(module, [point, ...]), ...]) from the notes' headings.

    Labels are shortened and their LaTeX is turned into plain text: an SVG has no math typesetting,
    so a heading like `## 5｜电偶极矩 $\\vec{p}$` would otherwise print its source on the map.
    """
    root = None
    modules = []
    for line in open(path, encoding="utf-8"):
        if line.startswith("```"):
            continue
        if line.startswith("### "):
            if modules:
                modules[-1][1].append(shorten(line[4:].strip()))
        elif line.startswith("## "):
            modules.append((shorten(line[3:].strip()), []))
        elif line.startswith("# ") and root is None:
            root = shorten(line[2:].strip())
    # A module with no knowledge points is document furniture, not structure.
    return root, [(m, pts) for m, pts in modules if pts]


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def node_svg(node, fill, stroke, text_fill, bold=False):
    out = [f'<rect x="{node.x:.1f}" y="{node.y:.1f}" width="{node.w:.1f}" '
           f'height="{node.h:.1f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>']
    if node.level == 2:                       # a slim accent bar marks each leaf
        out.append(f'<rect x="{node.x:.1f}" y="{node.y:.1f}" width="3.4" '
                   f'height="{node.h:.1f}" rx="1.7" fill="{stroke}"/>')
    weight = ' font-weight="600"' if bold else ""
    base = node.y + PAD_Y + node.size * 0.94
    for i, line in enumerate(node.lines):
        out.append(f'<text x="{node.x + PAD_X + (3.4 if node.level == 2 else 0):.1f}" '
                   f'y="{base + i * node.size * LINE_H:.1f}" font-family="{FONT}" '
                   f'font-size="{node.size:.1f}"{weight} fill="{text_fill}">{esc(line)}</text>')
    return out


def link(x1, y1, x2, y2, stroke):
    dx = (x2 - x1) * 0.55
    return (f'<path d="M {x1:.1f} {y1:.1f} C {x1 + dx:.1f} {y1:.1f}, '
            f'{x2 - dx:.1f} {y2:.1f}, {x2:.1f} {y2:.1f}" fill="none" '
            f'stroke="{stroke}" stroke-width="1.6" stroke-opacity="0.5"/>')


def build(title, modules, accents):
    root = Node(title, 0)
    mod_nodes = [Node(m, 1) for m, _ in modules]
    point_nodes = [[Node(p, 2) for p in pts] for _, pts in modules]

    col0 = MARGIN
    col1 = col0 + root.w + GAP_COL
    mod_w = max(n.w for n in mod_nodes)
    col2 = col1 + mod_w + GAP_COL
    total_w = col2 + max(n.w for band in point_nodes for n in band) + MARGIN

    bands = []
    for i, band in enumerate(point_nodes):
        stack = len(band) * GAP_POINT + sum(n.h for n in band) - GAP_POINT
        bands.append(max(mod_nodes[i].h, stack))
    total_h = sum(bands) + GAP_BAND * (len(bands) - 1) + 2 * MARGIN
    root.x, root.y = col0, MARGIN + (total_h - 2 * MARGIN - root.h) / 2

    y = MARGIN
    for i, band in enumerate(point_nodes):
        stack = len(band) * GAP_POINT + sum(n.h for n in band) - GAP_POINT
        mod_nodes[i].x = col1
        mod_nodes[i].y = y + (bands[i] - mod_nodes[i].h) / 2
        py = y + (bands[i] - stack) / 2
        for node in band:
            node.x, node.y = col2, py
            py += node.h + GAP_POINT
        y += bands[i] + GAP_BAND

    links, boxes = [], []
    for i, band in enumerate(point_nodes):
        accent = accents[i % len(accents)]
        links.append(link(root.right, root.cy, col1, mod_nodes[i].cy, accent))
        for node in band:
            links.append(link(mod_nodes[i].right, mod_nodes[i].cy, node.x, node.cy, accent))
        boxes += node_svg(mod_nodes[i], accent, accent, "#ffffff", bold=True)
        for node in band:
            boxes += node_svg(node, "#ffffff", accent, INK)

    return "\n".join(
        [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.0f} {total_h:.0f}" '
         f'width="{total_w:.0f}" height="{total_h:.0f}" role="img" aria-label="{esc(title)}">',
         f"<title>{esc(title)}</title>"]
        + links
        + node_svg(root, ROOT_FILL, ROOT_FILL, "#ffffff", bold=True)
        + boxes
        + ["</svg>"]
    )


def utf8_when_redirected():
    """Windows redirects stdout through the ANSI code page, so printing a CJK path raises
    UnicodeEncodeError and kills a run that had already finished. A console keeps its own
    encoding; only a redirected stream is switched to UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and not stream.isatty():
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main():
    utf8_when_redirected()
    ap = argparse.ArgumentParser(description="easy-learning mind map from notes headings")
    ap.add_argument("notes")
    ap.add_argument("-o", "--out")
    ap.add_argument("--insert", action="store_true",
                    help="insert or refresh the image reference in the notes")
    ap.add_argument("--alt", default="Mind map", help="caption / alt text (user's language)")
    ap.add_argument("--accent", default=",".join(ACCENTS))
    args = ap.parse_args()

    title, modules = parse(args.notes)
    if not title or not modules:
        sys.stderr.write("no `#` title with `##` modules and `###` points found\n")
        return 2

    accents = [a.strip() for a in args.accent.split(",") if a.strip()] or ACCENTS
    stem = os.path.splitext(os.path.basename(args.notes))[0]
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.notes)),
                                   f"{stem}.mindmap.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build(title, modules, accents))

    all_sections = sum(1 for line in open(args.notes, encoding="utf-8")
                       if re.match(r"^##\s", line))
    skipped = all_sections - len(modules)

    print(f"{out}: {len(modules)} modules, "
          f"{sum(len(p) for _, p in modules)} knowledge points"
          + (f", {skipped} appendix section(s) skipped" if skipped else ""))

    if args.insert:
        ref = f"![{args.alt}]({link_target(out)})"
        lines = open(args.notes, encoding="utf-8").read().split("\n")
        lines = [l for l in lines if l.strip() != ref and not l.startswith(f"![{args.alt}](")]
        first_module = next((i for i, l in enumerate(lines) if l.startswith("## ")), len(lines))
        while first_module > 0 and not lines[first_module - 1].strip():
            first_module -= 1
        lines[first_module:first_module] = ["", ref, ""]
        open(args.notes, "w", encoding="utf-8").write("\n".join(lines))
        print(f"inserted into {args.notes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
