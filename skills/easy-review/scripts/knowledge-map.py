#!/usr/bin/env python
"""easy-review -- draw the revision note's knowledge map from its own headings.

The notes' structure is the single source of truth. `#` is the root, each `##` module is a
branch, each `###` knowledge point is a leaf, and the `####` sub-points of a knowledge point
hang beside it in their own column -- they are numbered rules, cases or modes, not new leaves.

The sections that are not knowledge -- 自测 / self-test, 附录 / appendix, 报告 / report --
are skipped, so the map shows knowledge structure rather than the document's furniture.

Usage:
    python knowledge-map.py NOTES.md [-o OUT.svg] [--insert] [--before HEADING]
                                     [--root TITLE] [--alt CAPTION] [--scale 1.0]
                                     [--accent "#2f6fb5,#4a8a4a,..."]

Writes an SVG next to the notes. With --insert, also puts (or refreshes) the image reference
in the notes, above the first module it drew.

Exit codes: 0 ok | 2 nothing to draw
"""

import argparse
import os
import re
import sys

# --- typography -------------------------------------------------------------
FONT = "'Microsoft YaHei','PingFang SC','Hiragino Sans GB','Segoe UI',sans-serif"
SIZES = {0: 16.0, 1: 13.5, 2: 12.0, 3: 11.0}
LINE_H = 1.42
PAD_X = 14.0
PAD_Y = 9.0
# A module name is capped harder than the rest: a long one becomes a tall column of short
# lines, which is the cheapest way to lose vertical space in a wide map.
WRAP = {0: 234.0, 1: 168.0, 2: 320.0, 3: 250.0}

# Punctuation that must not be orphaned onto a line start, and openers that must not be
# left dangling at a line end. CJK closing marks and their ASCII counterparts.
NO_START = set("），,。、.；;：:％%！!？?）】」》…")
NO_END = set("（(【「《")

GAP_COL = 46.0        # horizontal gap between columns
GAP_LEAF = 9.0        # vertical gap between sibling knowledge points
GAP_BAND = 26.0       # vertical gap between module bands
GAP_SUB = 7.0         # vertical gap between a group label and its sub-points
MARGIN = 10.0
ROOT_SLOT = 30.0      # the root's own row height; the root is centred in it, not stretched

# A coherent set lifted from the notes stylesheet: deep blue first, then companions.
ACCENTS = ["#2f6fb5", "#4a8a4a", "#8a5a9e", "#b0712c", "#2c8a8a", "#a8517a"]
ROOT_FILL = "#1f3a5f"
GROUP_FILL = "#eef3f8"
GROUP_INK = "#3d4a58"
INK = "#1a1a1a"
WHITE = "#ffffff"

THIN = set("iljI.,:;'|!()[]")

# Plain-text equivalents so a label reads as `T²–L` rather than `T^2–L` in SVG, which has no
# math typesetting of its own.
SUPER = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
         "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻"}
SUB = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
       "6": "₆", "7": "₇", "8": "₈", "9": "₉"}

# A heading that names a part of the document rather than a piece of knowledge. Only
# document-furniture words belong here: a module called 练习 or 习题 is still a module.
NON_BODY = ("自测", "自检", "附录", "报告", "勘误", "纠错", "复习目标", "考前自检",
            "self-test", "self test", "test yourself", "quiz", "question bank",
            "appendix", "errata", "report", "review goals", "mastery checklist")
# Leading numbering on a heading: "3.2 ", "3.2、", "第 3 章：". Deliberately not `模块 3｜`:
# that prefix is part of how the module reads, and shortening it to "模块 3" helps nobody.
NUM_PREFIX = re.compile(r"^\s*\*{0,2}\s*(?:\d+(?:\.\d+)*\.?\s*[｜|、:：.．]?\s*|"
                        r"第\s*[一二三四五六七八九十百\d]+\s*[章节部分讲]+\s*[：:｜|]?\s*)")


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


def shorten(text, limit=110):
    """A heading is a label, not a sentence: drop markdown emphasis and keep one clause."""
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\s*\{#[^}]*\}\s*$", "", text)     # a heading anchor is not part of the name
    text = plain_math(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = NUM_PREFIX.sub("", text).strip() or text
    if len(text) > limit:
        # Prefer cutting at a clause boundary so the label still reads as a label.
        head = text[:limit]
        for mark in ("（", "(", "：", ":", "；", ";", "，", ",", " "):
            cut = head.rfind(mark)
            if cut > limit * 0.5:
                return head[:cut].rstrip() + "…"
        return head.rstrip() + "…"
    return text


def plain_math(text):
    """SVG text is not typeset, so `$T^2$–$L$` would print with its dollar signs.

    This is a label, not the formula: strip the delimiters, keep the symbols. The notes carry
    the typeset version; the map only has to be recognisable at a glance.
    """
    if "$" not in text and "\\" not in text:
        return text
    text = re.sub(r"\$([^$]*)\$", r"\1", text)
    for latex, glyph in (("\\pi", "π"), ("\\theta", "θ"), ("\\sigma", "σ"), ("\\Delta", "Δ"),
                         ("\\times", "×"), ("\\pm", "±"), ("\\sqrt", "√"), ("\\le", "≤"),
                         ("\\ge", "≥"), ("\\log", "log"), ("\\bar", ""), ("\\", "")):
        text = text.replace(latex, glyph)
    text = re.sub(r"\^\{?([0-9+-]+)\}?", lambda m: SUPER.get(m.group(1), "^" + m.group(1)), text)
    text = re.sub(r"_\{?([0-9A-Za-z]+)\}?", lambda m: SUB.get(m.group(1), "_" + m.group(1)), text)
    return text


class Node:
    def __init__(self, title, depth):
        self.title = title
        self.depth = min(depth, max(SIZES))
        self.size = SIZES[self.depth]
        self.label = shorten(title)
        self.lines = wrap(self.label, self.size, WRAP[self.depth])
        self.w = max(text_width(l, self.size) for l in self.lines) + 2 * PAD_X
        self.h = len(self.lines) * self.size * LINE_H + 2 * PAD_Y
        self.children = []
        self.rows = []              # a module's knowledge points, flattened from `band`
        self.band = []              # a module's rows: (lead knowledge point, *sub-points)
        self.body = ""
        self.x = self.y = 0.0

    @property
    def cy(self):
        return self.y + self.h / 2

    @property
    def right(self):
        return self.x + self.w


def is_non_body(title):
    low = title.lower()
    return any(key in title or key in low for key in NON_BODY)


def parse_headings(path):
    """[(level, title, body)] for every ATX heading, skipping fenced code blocks.

    `body` is the prose between this heading and the next one: it is what tells a knowledge
    point that carries its own text from one that only introduces sub-points.
    """
    out, fenced, current = [], False, None
    for raw in open(path, encoding="utf-8"):
        if raw.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = re.match(r"^(#{1,6})\s+(.*?)\s*$", raw)
        if match:
            current = {"level": len(match.group(1)), "title": match.group(2), "body": []}
            out.append(current)
            continue
        if current is not None:
            current["body"].append(raw.rstrip("\n"))
    for entry in out:
        entry["body"] = "\n".join(entry["body"]).strip()
    return out


def build_tree(headings):
    """Turn the heading list into one root -> module -> knowledge-point tree.

    The document's `#` becomes the map root, so its depth is the root's depth and every other
    heading sits one level under its parent. The stack is `(heading level, node)`; comparing
    levels rather than depths is what lets a `###` close its `##` without also closing the `#`.
    """
    if not headings:
        return Node("map", 0)
    top_level = min(e["level"] for e in headings)
    top = next(e for e in headings if e["level"] == top_level)
    root = Node(top["title"], 0)
    root.heading_level = top_level
    stack = [(1, root)]
    for entry in headings:
        if entry is top:
            continue
        level = entry["level"] - top_level + 1      # normalise so the root's level is 1
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()
        node = Node(entry["title"], stack[-1][1].depth + 1)
        node.body = entry["body"]
        node.heading_level = entry["level"]
        stack[-1][1].children.append(node)
        stack.append((level, node))

    for module in root.children:
        rows = []
        for child in module.children:
            # `####` headings are sub-points of their `###` parent, whether or not the parent
            # also has an intro sentence: those are numbered rules, cases, or modes, and the
            # reading order is already parent-then-children.
            subs = child.children
            for start in range(0, max(len(subs), 1), SUBS_PER_ROW):
                chunk = subs[start:start + SUBS_PER_ROW]
                rows.append(([child] if start == 0 else [None]) + chunk)
        module.band = [tuple(r) for r in rows]
        module.rows = [n for r in rows for n in r if n is not None]
    return root


SUBS_PER_ROW = 2      # sub-points drawn beside their group label before wrapping to a new row


def band_extent(band):
    """Distance from the band's left edge to its rightmost node.

    A group label puts its sub-points in a column of their own, one GAP_COL to the right, at
    most SUBS_PER_ROW per row. Spreading every sub-point along one line instead would be wider
    than it is tall, and a map wider than a page has to shrink until it cannot be read.
    """
    width = 0.0
    for row in band:
        lead = row[0]
        x = 0.0 if lead is None else lead.w
        if len(row) > 1:
            x += GAP_COL + sum(n.w for n in row[1:]) + GAP_COL * (len(row) - 2)
        width = max(width, x)
    return width


def place_band(band, x, y):
    """Assign every node in one module's band, and return the band's own height."""
    top = y
    for row in band:
        lead = row[0]
        row_y = y
        if lead is not None:
            lead.x, lead.y = x, y
        sx = x + (0.0 if lead is None else lead.w + GAP_COL)
        for sub in row[1:]:
            sub.x, sub.y = sx, row_y
            sx += sub.w + GAP_COL
        y += row_height(row) + GAP_LEAF
    return y - GAP_LEAF - top


def row_height(row):
    return max((n.h for n in row if n is not None), default=0.0)


def band_height(band):
    if not band:
        return 0.0
    return sum(row_height(r) for r in band) + GAP_LEAF * (len(band) - 1)


def build_plan(root):
    """Resolve the whole geometry first, then draw it.

    Measuring and drawing the same tree twice is where a clipping bug hides; one plan is the
    only description of where anything sits. Three columns: the root, the module labels, and
    the knowledge points with their sub-point columns.
    """
    modules = [m for m in root.children if m.band]
    if not modules:
        return None
    extents = [band_extent(m.band) for m in modules]
    heights = [max(m.h, band_height(m.band)) for m in modules]
    points_x = root.w + GAP_COL + max(m.w for m in modules) + GAP_COL
    total_w = points_x + max(extents) + MARGIN
    total_h = 2 * MARGIN + max(root.h, ROOT_SLOT) + GAP_BAND \
        + sum(heights) + GAP_BAND * (len(modules) - 1)

    root.x = MARGIN
    root.y = MARGIN + (max(root.h, ROOT_SLOT) - root.h) / 2
    y = MARGIN + max(root.h, ROOT_SLOT) + GAP_BAND
    for module, height in zip(modules, heights):
        module.x = root.w + GAP_COL
        module.y = y + (height - module.h) / 2
        place_band(module.band, points_x, y)
        y += height + GAP_BAND
    return total_w, total_h, modules


def measure(node, text):
    """Size one node from its text: the map is geometry derived from strings, nothing else."""
    node.lines = wrap(text, node.size, WRAP[node.depth])
    node.w = max(text_width(l, node.size) for l in node.lines) + 2 * PAD_X
    node.h = len(node.lines) * node.size * LINE_H + 2 * PAD_Y


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def node_svg(node, fill, stroke, text_fill, bold=False):
    out = [f'<rect x="{node.x:.1f}" y="{node.y:.1f}" width="{node.w:.1f}" '
           f'height="{node.h:.1f}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>']
    if node.depth >= 2:                       # a slim accent bar marks each knowledge point
        out.append(f'<rect x="{node.x:.1f}" y="{node.y:.1f}" width="3.4" '
                   f'height="{node.h:.1f}" rx="1.7" fill="{stroke}"/>')
    weight = ' font-weight="600"' if bold else ""
    base = node.y + PAD_Y + node.size * 0.94
    offset = 3.4 if node.depth >= 2 else 0.0
    for i, line in enumerate(node.lines):
        out.append(f'<text x="{node.x + PAD_X + offset:.1f}" '
                   f'y="{base + i * node.size * LINE_H:.1f}" font-family="{FONT}" '
                   f'font-size="{node.size:.1f}"{weight} fill="{text_fill}">{esc(line)}</text>')
    return out


def link(x1, y1, x2, y2, stroke):
    dx = (x2 - x1) * 0.55
    return (f'<path d="M {x1:.1f} {y1:.1f} C {x1 + dx:.1f} {y1:.1f}, '
            f'{x2 - dx:.1f} {y2:.1f}, {x2:.1f} {y2:.1f}" fill="none" '
            f'stroke="{stroke}" stroke-width="1.6" stroke-opacity="0.5"/>')


def build(title, root, accents, scale):
    """Render the map. The root's own label is the only text that comes from outside headings."""
    measure(root, title)
    plan = build_plan(root)
    if plan is None:
        raise SystemExit("nothing to draw")
    total_w, total_h, modules = plan

    links, boxes = [], []
    for i, module in enumerate(modules):
        accent = accents[i % len(accents)]
        links.append(link(root.right, root.cy, module.x, module.cy, accent))
        boxes += node_svg(module, accent, accent, WHITE, bold=True)
        for row in module.band:
            lead = row[0]
            if lead is not None:
                grouped = bool(lead.children)
                fill, ink, bold = ((GROUP_FILL, GROUP_INK, True) if grouped
                                   else (WHITE, INK, False))
                boxes += node_svg(lead, fill, accent, ink, bold=bold)
                links.append(link(module.right, module.cy, lead.x, lead.cy, accent))
            for sub in row[1:]:
                boxes += node_svg(sub, WHITE, accent, INK)
                links.append(link(lead.right if lead is not None else module.right,
                                  lead.cy if lead is not None else module.cy,
                                  sub.x, sub.cy, accent))

    head = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w:.1f} {total_h:.1f}" '
            f'width="{total_w * scale:.0f}" height="{total_h * scale:.0f}" '
            f'role="img" aria-label="{esc(title)}">',
            f"<title>{esc(title)}</title>"]
    if scale != 1.0:
        head.append(f'<g transform="scale({scale:.4f})">')
        tail = ["</g>", "</svg>"]
    else:
        tail = ["</svg>"]
    return "\n".join(head + links
                     + node_svg(root, ROOT_FILL, ROOT_FILL, WHITE, bold=True)
                     + boxes + tail)


def main():
    ap = argparse.ArgumentParser(description="easy-review knowledge map from notes headings")
    ap.add_argument("notes")
    ap.add_argument("-o", "--out")
    ap.add_argument("--insert", action="store_true",
                    help="insert or refresh the image reference in the notes")
    ap.add_argument("--before", help="insert above the first `##` whose text contains this")
    ap.add_argument("--root", help="override the map's root label (default: the notes' H1)")
    ap.add_argument("--alt", default="Knowledge map",
                    help="caption / alt text (the user's language)")
    ap.add_argument("--scale", type=float, default=1.0, help="print scale, e.g. 0.82")
    ap.add_argument("--accent", default=",".join(ACCENTS))
    args = ap.parse_args()

    headings = parse_headings(args.notes)
    h1 = next((h for h in headings if h["level"] == 1), None)
    if not h1:
        sys.stderr.write("no `#` title found\n")
        return 2

    tree = build_tree(headings)
    modules = [m for m in tree.children if m.band]
    if not modules:
        sys.stderr.write("no `##` modules with knowledge points found\n")
        return 2

    title = shorten(args.root or h1["title"], 120)
    accents = [a.strip() for a in args.accent.split(",") if a.strip()] or ACCENTS
    stem = os.path.splitext(os.path.basename(args.notes))[0]
    out = args.out or os.path.join(os.path.dirname(os.path.abspath(args.notes)),
                                   f"{stem}.mindmap.svg")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build(title, tree, accents, args.scale))

    points = sum(len(m.rows) for m in modules)
    skipped = sum(1 for h in headings if h["level"] == 2 and is_non_body(h["title"]))
    print(f"{out}: {len(modules)} modules, {points} knowledge points"
          + (f", {skipped} non-knowledge section(s) skipped" if skipped else ""))

    if args.insert:
        ref = f"![{args.alt}]({os.path.basename(out)})"
        lines = open(args.notes, encoding="utf-8").read().split("\n")
        # Refresh, never duplicate: drop this exact reference wherever it already sits.
        lines = [l for l in lines if l.strip() != ref]
        anchor = len(lines)
        for i, line in enumerate(lines):
            if args.before:
                if line.startswith("## ") and args.before in line:
                    anchor = i
                    break
            elif line.startswith("## ") and not is_non_body(line[3:].strip()):
                anchor = i
                break
        while anchor > 0 and not lines[anchor - 1].strip():
            anchor -= 1
        lines[anchor:anchor] = ["", ref, ""]
        open(args.notes, "w", encoding="utf-8").write("\n".join(lines))
        print(f"inserted into {args.notes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
