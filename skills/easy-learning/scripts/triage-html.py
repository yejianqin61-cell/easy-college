#!/usr/bin/env python
"""easy-learning -- unit triage for HTML courseware.

An HTML deck has no page objects: it has markup. This script decides what a "page" is for the
file it is given -- one row per slide, section or document -- and gives every row a verdict, in
the same ledger the PDF path writes, so steps 2-7 read both formats identically.

It is deliberately standard-library only: reading an HTML deck must not depend on a package that
may not be installed. Renders (for the vision pass) are optional and need a browser.

Usage:
    python triage-html.py DECK.html [DECK2.html ...] [--out DIR] [--slide-selector SEL]
                          [--render] [--dpi 150] [--no-dump]

    --slide-selector "section.slide"   force the unit element when auto-detection is wrong

Writes <out>/<name>/ledger.json, <out>/<name>/ledger.md, <out>/<name>.slides.md and, with
--render, <out>/<name>/pages/<name>-sNN.png. Merges its entry into <out>/sources.json.

Exit codes: 0 ok | 2 input could not be read
"""

import argparse
import collections
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser

THIN_TEXT_CHARS = 120      # below this a unit has too little text to be sure of it
SHELL_TEXT_CHARS = 1000    # a unit framing a local file and thinner than this is a shell
FRAME_MIN_BYTES = 1024     # a smaller framed file is a warm-up or tracking frame, not content
FULL_BLEED_MEDIAN = 0.50   # median image share this high means every unit is mostly pictures
DUP_MIN = 0.85             # token-set overlap with the previous unit
NOISE_PAGE_SHARE = 0.90    # a token on this share of units, about once each, is furniture
NOISE_PER_UNIT_MAX = 1.5   # furniture repeats once per unit; content vocabulary repeats often
ALT_RECOVER_CHARS = 60     # alt text this long makes a picture recoverable without eyes
NEST_MAX_DEPTH = 8         # how far a wrapper of <section>s may nest before it is suspicious

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
        "source", "track", "wbr"}
RAW_TEXT = {"script", "style"}                      # content is not prose
SKIP_SUBTREE = {"head", "script", "style", "template", "noscript", "title", "meta", "link"}
BLOCK = {"p", "div", "section", "article", "aside", "header", "footer", "main", "li", "tr",
         "td", "th", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote", "figure",
         "figcaption", "dt", "dd", "table", "ul", "ol", "dl", "details", "summary"}
TEXT_BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "pre", "blockquote",
              "figcaption", "dd"}
# Elements that carry prose rather than a page. A run of them is a paragraph, not a deck.
PROSE_TAGS = {"p", "li", "td", "th", "pre", "blockquote", "figcaption", "dt", "dd", "span",
              "a", "em", "strong", "code", "label", "output"}

# Speaker notes: the plural convention, and only that. `class="note"` is a visible callout box in
# most course handouts, so matching the singular turns body text into a private channel.
NOTES_CLASS = re.compile(r"(?:^|[^a-z])(?:notes|speaker-notes|presenter-notes|speaker-note)"
                         r"(?:[^a-z]|$)", re.I)
FRAGMENT_CLASS = re.compile(r"(?:^|[^a-z])fragment(?:[^a-z]|$)", re.I)
MATH_IMG = re.compile(r"(katex|mathjax|equation|formula|\bmath\b|\blatex\b)", re.I)
# A formula said in words -- the accessible label of a hand-built formula block. These labels are
# how a reader who cannot see the fraction gets it, and they are the recovery for flattened markup.
MATH_WORDS = re.compile(r"\b(equals?|divided by|times|multiplied by|squared|cubed|integral|"
                        r"vector|plus|minus|root|per)\b", re.I)
# Classes that mean "this element is a formula built out of spans" -- the layout the text layer
# cannot carry: a `.frac` flattens to its numerator glued to its denominator.
FORMULA_CLASS = re.compile(r"(?:^|[^a-z])(frac|sqrt|vec|overset|underset|equation|formula)"
                           r"(?:[^a-z]|$)", re.I)
CSS_HIDDEN = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)
# Class tokens decks use to mark one slide.
SLIDE_CLASSES = {"slide", "slides", "marp-slide", "remark-slide", "step", "shower", "page",
                 "deck", "slide-container", "slide-content"}
SLIDE_ATTRS = ("data-slide", "data-slide-number", "data-index", "data-marpit-svg", "data-step")
# Framework state classes, added at run time by reveal.js & friends. A saved DOM carries them, and
# they mean "not the current slide", not "the author hid this".
FRAMEWORK_STATE = {"present", "past", "future", "next", "previous", "active", "current",
                   "visible", "shown", "stack"}
# Class names that mean "not on the screen". A stylesheet is not always inlined, so the name is
# the signal, and the list is deliberately short: a false `hidden-content` costs a human a look,
# but a false positive on every unit costs the ledger its credibility.
HIDDEN_TOKENS = {"hidden", "invisible", "nodisplay", "no-display", "d-none", "display-none",
                 "hidden-content"}
# Class names that hide an answer. Kept separate because the CSS-derived rule accepts these too,
# and `class="answer"` alone is a legitimate authoring pattern.
ANSWER_TOKENS = {"answer", "answers", "solution", "solutions", "secret", "quiz-answer"}


class Node:
    """One element. Children are Nodes and strings."""

    __slots__ = ("tag", "attrs", "children", "parent", "raw")

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []
        self.parent = None
        self.raw = ""            # text content of <script>/<style>, kept verbatim


class Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {})
        self.stack = [self.root]
        self.raw_node = None

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k.lower(): (v if v is not None else "") for k, v in attrs})
        self.stack[-1].children.append(node)
        node.parent = self.stack[-1]
        if tag in VOID:
            return
        self.stack.append(node)
        if tag in RAW_TEXT:
            self.raw_node = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.raw_node is not None and tag == self.raw_node.tag:
            self.raw_node = None
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.raw_node is not None:
            self.raw_node.raw += data
            return
        self.stack[-1].children.append(data)


def element_children(node):
    return [c for c in node.children if isinstance(c, Node)]


def walk(node):
    for child in element_children(node):
        yield child
        for sub in walk(child):
            yield sub


def classes(node):
    return set((node.attrs.get("class") or "").split())


def find_body(root):
    for node in walk(root):
        if node.tag == "body":
            return node
    return root


def text_of(root, separator=" "):
    """Every string in a subtree, ignoring script/style/head."""
    out = []
    for node in [root] + list(walk(root)):
        if node.tag in SKIP_SUBTREE:
            continue
        for child in node.children:
            if isinstance(child, str) and child.strip():
                out.append(child)
    return separator.join(out)


def ancestors(node):
    out = []
    while node.parent is not None:
        node = node.parent
        out.append(node)
    return out


def collapse(text):
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# --------------------------------------------------------------------------- unit detection

def parse_selector(spec):
    """A tiny CSS subset: comma-separated `tag`, `.class`, `#id`, `tag.class`, `[attr]`,
    `[attr=value]`. Anything else is a syntax error, not a silent no-match."""
    parts = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.fullmatch(
            r"([a-zA-Z][\w-]*)?(?:\.([\w-]+))?(?:#([\w-]+))?"
            r"(?:\[([\w-]+)(?:=[\"']?([^\]\"']*)[\"']?)?\])?", chunk)
        if not m or not any(m.groups()):
            raise ValueError(f"unsupported selector: {chunk!r}")
        parts.append({"tag": (m.group(1) or "").lower(), "class": m.group(2), "id": m.group(3),
                      "attr": m.group(4), "value": m.group(5)})
    if not parts:
        raise ValueError("empty selector")
    return parts


def matches_selector(node, parts):
    for part in parts:
        if part["tag"] and node.tag != part["tag"]:
            continue
        if part["class"] and part["class"] not in classes(node):
            continue
        if part["id"] and node.attrs.get("id") != part["id"]:
            continue
        if part["attr"]:
            if part["attr"] not in node.attrs:
                continue
            if part["value"] is not None and node.attrs.get(part["attr"]) != part["value"]:
                continue
        return True
    return False


def marked_slide(node):
    if any(a in node.attrs for a in SLIDE_ATTRS):
        return True
    return bool(classes(node) & SLIDE_CLASSES)


def descend_nested(units, depth=0):
    """A `<section>` holding only `<section>`s is a vertical stack: the children are the slides.

    Only `section` children are descended into -- a two-column slide is also a node with several
    children, and splitting it would invent pages that do not exist. A wrapper holding a title and
    its sections is still a stack, so the wrapper's *own* text decides.
    """
    if depth > NEST_MAX_DEPTH:
        return units
    out = []
    for unit in units:
        kids = [c for c in element_children(unit) if c.tag == "section"]
        others = [c for c in element_children(unit) if c.tag != "section"]
        own = collapse(" ".join(text_of(c) for c in others))
        # A sole child is a wrapper (`<div class="slides"><section>` holding the deck), not a slide
        # with one part, so it is always looked through.
        if (len(kids) >= 2 or (len(kids) == 1 and not others)) and len(own) < THIN_TEXT_CHARS:
            out.extend(descend_nested(kids, depth + 1))
        else:
            out.append(unit)
    return out


def unwrap_single(hits):
    """A single match holding the slides (`<div class="slides">`) is the container, not a unit."""
    if len(hits) == 1 and len(element_children(hits[0])) >= 2:
        return element_children(hits[0])
    return hits


def sibling_group(body, body_chars, min_size=3):
    """The largest run of same-tag siblings holding the document's text -- the generic shape.

    Prose elements are never units: three `<p>` siblings are a paragraph, not three pages, and
    treating them as pages hides the headings that really do divide the document.
    """
    best = (None, [])
    for parent in [body] + list(walk(body)):
        by_tag = collections.defaultdict(list)
        for child in element_children(parent):
            by_tag[child.tag].append(child)
        for tag, group in by_tag.items():
            if len(group) < min_size or len(group) <= len(best[1]) or tag in PROSE_TAGS:
                continue
            share = sum(len(text_of(g)) for g in group) / max(1, body_chars)
            if share >= 0.60:
                best = (tag, group)
    return best


def heading_units(body):
    """Slice the document at its top-level headings: one unit per heading and its content."""
    for level in range(1, 7):
        tag = f"h{level}"
        heads = [n for n in walk(body) if n.tag == tag]
        tops = [h for h in heads if not any(a.tag == tag for a in ancestors(h))]
        if len(tops) < 2:
            continue
        parent = tops[0].parent
        if parent is None or any(h.parent is not parent for h in tops):
            continue
        marks = [parent.children.index(h) for h in tops]
        units = []
        for i, start in enumerate(marks):
            end = marks[i + 1] if i + 1 < len(marks) else len(parent.children)
            wrapper = Node("div", {})
            wrapper.children = parent.children[start:end]
            wrapper.parent = parent
            units.append(wrapper)
        return units, tag
    return [], None


def detect_units(root, body, selector):
    """(units, model) -- the partition this file's verdicts will be about."""
    if selector:
        parts = parse_selector(selector)
        hits = [n for n in walk(body) if matches_selector(n, parts)]
        hits = [n for n in hits if not any(matches_selector(a, parts) for a in ancestors(n))]
        if not hits:
            return [], "forced-selector-no-match"
        return descend_nested(unwrap_single(hits)), "forced-selector"

    # 1. the deck says so: a slide class or a slide attribute
    hits = [n for n in walk(body) if marked_slide(n)]
    hits = [n for n in hits if not any(marked_slide(a) for a in ancestors(n))]
    if hits:
        units = descend_nested(unwrap_single(hits))
        if len(units) >= 2:
            return units, "marked-slides"

    # 2. <section> is the other common slide element (reveal.js, Quarto, semantic pages)
    sections = [n for n in walk(body) if n.tag == "section"]
    if len(sections) >= 2:
        tops = [s for s in sections if not any(a.tag == "section" for a in ancestors(s))]
        units = descend_nested(tops if tops else sections)
        if len(units) >= 2:
            return units, "sections"

    # 3. a run of same-tag siblings holding the document's text
    tag, group = sibling_group(body, len(text_of(body)))
    if group:
        return group, f"sibling-{tag}s"

    # 4. an article-like page: one unit per top-level heading and what follows it
    units, tag = heading_units(body)
    if len(units) >= 2:
        return units, f"heading-{tag}"

    # 5. the whole file is one unit, and the ledger says so rather than inventing pages
    return [body], "single-document"


def unit_word_for(model):
    if model in ("marked-slides", "forced-selector"):
        return "slide"
    if model == "sections" or model.startswith("heading-"):
        return "section"
    if model == "single-document":
        return "document"
    return "unit"


# --------------------------------------------------------------------------- per-unit scan

class Scan:
    def __init__(self):
        self.text = []
        self.notes = []
        self.hidden = []
        self.latex = []
        self.labels = []              # formula descriptions in words (aria-label / title)
        self.formula_blocks = 0       # hand-built formula markup: .frac, .vec, .sqrt
        self.formula_markup = []      # the markup itself, which is the recovery
        self.math_nodes = []          # [{"text": MathML approximation, "tex": bool}]
        self.images = 0
        self.images_noalt = 0
        self.alt_chars = 0
        self.alts = []                # (src, alt) for the dump
        self.containers = 0           # empty elements a script is expected to fill
        self.math_img = 0
        self.svg_content = 0
        self.frames = 0
        self.fragments = 0
        self.text_blocks = 0
        self.hidden_self = False
        self.hidden_desc = False

    def visible(self):
        return collapse("".join(self.text))


def hidden_selectors(root):
    """Class/id selectors whose rule hides an element.

    A tag selector is deliberately ignored: reveal.js ships `.reveal .slides > section
    {display:none}` and a cascade-blind reader that honoured it would call every slide hidden. The
    narrow class/id case (`.answer{display:none}`) is the one worth catching.
    """
    out = set()
    for node in walk(root):
        if node.tag != "style" or not node.raw:
            continue
        for selectors, decls in re.findall(r"([^{}]+)\{([^{}]*)\}", node.raw):
            if not CSS_HIDDEN.search(decls):
                continue
            for sel in selectors.split(","):
                simple = re.split(r"[ >+~]+", sel.strip())[-1]
                if not simple:
                    continue
                if simple[0] in ".#" and simple[1:] in HIDDEN_TOKENS | ANSWER_TOKENS:
                    out.add(simple)
    return out


def inside_control(node):
    """True inside a button or a link: an image there is an icon, not the page's content."""
    return any(a.tag in ("button", "a", "nav", "header", "footer") for a in ancestors(node))


def hidden_mechanism(node, selectors):
    """The mechanism that keeps this element off the screen, or None.

    Two exclusions, both learned from real decks. Fragments (`class="fragment"`) are content the
    framework reveals on the next click, so "hidden until clicked" is presentation state. And
    `aria-hidden` hides from a screen reader, not from the screen -- half the icons on a page carry
    it -- so it is not evidence of anything.
    """
    if FRAGMENT_CLASS.search(node.attrs.get("class") or "") or "data-fragment-index" in node.attrs:
        return None
    if classes(node) & FRAMEWORK_STATE and node.tag != "section":
        return None
    if node.tag == "template":
        return "template"
    if "hidden" in node.attrs:
        return "hidden-attr"
    inline = (node.attrs.get("style") or "").replace(" ", "").lower()
    if "display:none" in inline or "visibility:hidden" in inline:
        return "inline-style"
    cls, ident = classes(node), node.attrs.get("id") or ""
    for sel in sorted(selectors):
        if (sel.startswith(".") and sel[1:] in cls) or (sel.startswith("#") and sel[1:] == ident):
            return f"css {sel}"
    if cls & HIDDEN_TOKENS:
        return f"class {'/'.join(sorted(cls & HIDDEN_TOKENS))}"
    return None


def mathml_text(node):
    """A linear approximation of a MathML subtree, for the dump. Lossy by construction."""
    parts = [text_of(sub) for sub in [node] + list(walk(node))
             if sub.tag in ("mi", "mn", "mo", "mtext", "ms")]
    return collapse(" ".join(p for p in parts if p))


def raw_html(node, limit=240):
    """A hand-built formula block, tags and all.

    This is the recovery for flattened formula text: `<span class="frac"><span>a</span>
    <span>b</span></span>` is a over b, and saying so beats both guessing and a screenshot.
    """
    out, stop = [], [False]

    def emit(item):
        if stop[0]:
            return
        if isinstance(item, str):
            out.append(re.sub(r"\s+", " ", item))
        elif item.tag in ("script", "style"):
            return
        else:
            attrs = "".join(f' {k}="{item.attrs[k]}"' for k in ("class", "id")
                            if item.attrs.get(k))
            out.append(f"<{item.tag}{attrs}>")
            for child in item.children:
                emit(child)
            out.append(f"</{item.tag}>")
        if sum(len(part) for part in out) > limit * 2:
            stop[0] = True

    emit(node)
    text = "".join(out).strip()
    return text if len(text) <= limit else text[:limit] + "…"


def scan(unit, selectors):
    """One row's evidence: visible text, hidden text, notes, math, images, frames, fragments."""
    result = Scan()
    math_stack = []

    def visit(node, hidden_by, in_notes):
        if node.tag in SKIP_SUBTREE:
            if node.tag == "template":
                hidden_text = text_of(node)
                if hidden_text.strip():
                    result.hidden.append(hidden_text)
            return
        mechanism = hidden_by or hidden_mechanism(node, selectors)
        note_container = in_notes or (node.tag in ("aside", "div", "section", "p") and
                                      NOTES_CLASS.search(node.attrs.get("class") or ""))
        if mechanism:
            if node is unit:
                result.hidden_self = True
            else:
                result.hidden_desc = True
        if note_container:
            result.notes.append(text_of(node))
            return
        if node.tag in ("iframe", "frame") and not mechanism:
            src = (node.attrs.get("src") or "").strip()
            if src:
                result.frames += 1
                result.text.append(f"[frame src] {src}\n")
        if node.tag == "math":
            math_stack.append({"text": mathml_text(node), "tex": False})
        for attr in ("aria-label", "title"):
            value = (node.attrs.get(attr) or "").strip()
            if value and MATH_WORDS.search(value) and len(text_of(node)) < 300:
                result.labels.append(f"{attr}: {value}")
                break
        if node.tag != "img" and FORMULA_CLASS.search(node.attrs.get("class") or ""):
            result.formula_blocks += 1
            if len(result.formula_markup) < 8:
                result.formula_markup.append(raw_html(node))
        if node.tag == "annotation" and "tex" in (node.attrs.get("encoding") or "").lower():
            tex = text_of(node)
            if tex.strip():
                result.latex.append(tex)
                if math_stack:
                    math_stack[-1]["tex"] = True
        if node.tag == "script" and re.match(r"\s*math/tex", node.attrs.get("type") or ""):
            result.latex.append(node.raw.strip())
        if node.tag == "svg" and not inside_control(node) and \
                (node.attrs.get("aria-hidden") or "").lower() != "true":
            result.svg_content += 1
        if FRAGMENT_CLASS.search(node.attrs.get("class") or "") or \
                "data-fragment-index" in node.attrs:
            result.fragments += 1
        if node.tag == "img":
            result.images += 1
            alt = (node.attrs.get("alt") or "").strip()
            if alt:
                result.alt_chars += len(alt)
            else:
                result.images_noalt += 1
            result.alts.append(((node.attrs.get("src") or "").strip(), alt))
            hay = " ".join((node.attrs.get("class") or "", node.attrs.get("src") or "", alt))
            if MATH_IMG.search(hay):
                result.math_img += 1
            if mechanism:
                result.hidden.append(f"[img] {alt or node.attrs.get('src', '')}")
            return
        # An empty element carrying an id or a class is a placeholder a script fills in: the
        # signature of a deck whose slides are built at run time.
        if node.tag in ("div", "span", "canvas", "figure", "table") and not mechanism and \
                (node.attrs.get("id") or node.attrs.get("class")) and \
                not collapse(text_of(node)):
            result.containers += 1
        if node.tag in TEXT_BLOCK and any(isinstance(c, str) and c.strip() for c in node.children):
            result.text_blocks += 1
        if node.tag in BLOCK:
            result.text.append("\n\n")
        if node.tag in ("b", "strong"):
            result.text.append("**")             # the lecture's own emphasis survives the dump
        for child in node.children:
            if isinstance(child, str):
                if child.strip():
                    (result.hidden if mechanism else result.text).append(child)
            else:
                visit(child, mechanism, note_container)
        if node.tag in ("b", "strong"):
            result.text.append("**")
        if node.tag in BLOCK:
            result.text.append("\n" if node.tag in ("li", "tr", "td", "th") else "\n\n")
        if node.tag == "math":
            result.math_nodes.append(math_stack.pop())

    visit(unit, None, False)
    # An empty hidden placeholder -- `<div class="feedback" hidden=""></div>`, the usual way a page
    # reserves space for a script -- hides nothing, so it is not a finding.
    if not collapse(" ".join(result.hidden)):
        result.hidden_self = result.hidden_desc = False
        result.hidden = []
    return result


def token_set(text):
    return set(re.sub(r"\s+", " ", text).strip().split())


def local_frames(root, base_dir, selectors):
    """Local files this document frames -- usually where its content actually lives.

    A warm-up frame, a tracking pixel and a hidden iframe are frames too, so each is marked rather
    than dropped: only `content` frames are worth triaging, and the ledger says why the others are
    not.
    """
    out = []
    for node in walk(root):
        if node.tag not in ("iframe", "frame"):
            continue
        src = (node.attrs.get("src") or "").strip()
        if not src or re.match(r"^(https?:|data:|about:|#|javascript:)", src, re.I):
            continue
        hidden = any(a.tag == "template" or hidden_mechanism(a, selectors)
                     for a in [node] + ancestors(node))
        path = os.path.normpath(os.path.join(base_dir, src.split("?")[0].split("#")[0]))
        exists = os.path.isfile(path)
        size = os.path.getsize(path) if exists else 0
        out.append({"src": src, "path": path, "exists": exists, "bytes": size,
                    "hidden": bool(hidden),
                    "content": bool(exists and not hidden and size >= FRAME_MIN_BYTES)})
    return out


def triage_html(path, out_dir, dump, render, dpi, selector, browser):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        source = fh.read()
    parser = Tree()
    parser.feed(source)
    root = parser.root
    body = find_body(root)

    units, model = detect_units(root, body, selector)
    selectors = hidden_selectors(root)
    frames = local_frames(root, os.path.dirname(os.path.abspath(path)), selectors)
    script_present = any(node.tag == "script" for node in walk(root))

    rows, dumps, texts = [], [], []
    prev_tokens = None
    for number, unit in enumerate(units, 1):
        found = scan(unit, selectors)
        text = found.visible()
        tokens = token_set(text)
        dup = 0.0
        if prev_tokens:
            union = len(tokens | prev_tokens)
            dup = len(tokens & prev_tokens) / union if union else 0.0
        prev_tokens = tokens

        chars = len(text)
        images, blocks = found.images, found.text_blocks
        image_share = round(images / (images + blocks), 3) if (images + blocks) else 0.0
        math_tex = len(found.latex)
        mathml_only = sum(1 for node in found.math_nodes if not node["tex"])
        traps = []
        if found.hidden_self:
            traps.append("hidden-slide")
        elif found.hidden_desc:
            traps.append("hidden-content")
        if found.frames and chars < SHELL_TEXT_CHARS:
            traps.append("frame-shell")          # the content is in the framed file
        if chars < THIN_TEXT_CHARS and not images and script_present and \
                (blocks == 0 or found.containers):
            traps.append("js-rendered")          # nothing but a placeholder, filled in by script
        if found.math_img:
            traps.append("math-image")
        if found.math_nodes or found.latex or re.search(r"\\\(|\\\[", text):
            traps.append("math-source")
        if found.formula_blocks:
            traps.append("formula-markup")       # the text flattened; the label may carry it
        if images and chars < THIN_TEXT_CHARS:
            traps.append("image-alt" if found.alt_chars >= ALT_RECOVER_CHARS else "image-only")
        if not images and found.svg_content and chars < THIN_TEXT_CHARS:
            traps.append("svg-only")             # a vector diagram with no text around it
        if found.fragments:
            traps.append("fragments")
        if found.notes:
            traps.append("speaker-notes")
        if dup >= DUP_MIN:
            traps.append("duplicate")

        verdict = "readable"
        for trap, level in (("frame-shell", "needs-human"), ("hidden-slide", "needs-human"),
                            ("hidden-content", "needs-human"), ("js-rendered", "needs-vision"),
                            ("image-only", "needs-vision"), ("math-image", "needs-vision"),
                            ("svg-only", "needs-vision")):
            if trap in traps:
                verdict = level
                break

        rows.append({"src": os.path.basename(path), "page": number, "label": f"s{number:02d}",
                     "chars": chars, "raster": image_share, "traps": traps, "verdict": verdict,
                     "images": images, "images_noalt": found.images_noalt,
                     "alt_chars": found.alt_chars,
                     "math": {"count": len(found.math_nodes), "tex": math_tex,
                              "mathml_only": mathml_only, "image": found.math_img},
                     "formula_blocks": found.formula_blocks, "labels": len(found.labels),
                     "svg": found.svg_content, "frames": found.frames,
                     "fragments": found.fragments,
                     "notes_chars": len(collapse(" ".join(found.notes))),
                     "hidden_by": ("self" if found.hidden_self else
                                   ("descendant" if found.hidden_desc else "")),
                     "dup": round(dup, 2)})
        texts.append(text)
        dumps.append(render_dump(rows[-1], text, found))

    # Baseline: a deck that is pictures on every unit makes the image share useless as a per-unit
    # signal, exactly as a full-bleed PDF does. Report it once, at document level.
    baseline = statistics.median([r["raster"] for r in rows]) if rows else 0.0
    full_bleed = baseline >= FULL_BLEED_MEDIAN
    if full_bleed:
        for row in rows:
            if row["chars"] < THIN_TEXT_CHARS:
                for trap in ("image-only", "image-alt"):
                    if trap in row["traps"]:
                        row["traps"].remove(trap)
                row["traps"].append("empty-text" if row["chars"] == 0 else "thin-text")
                if row["verdict"] == "readable":
                    row["verdict"] = "needs-vision"

    # Master noise: furniture repeats about once per unit, whereas content vocabulary repeats
    # many times, so the occurrence rate is what separates a running head from "charge".
    threshold = max(2, int(len(rows) * NOISE_PAGE_SHARE))
    seen, total = collections.defaultdict(set), collections.Counter()
    for row, text in zip(rows, texts):
        tokens = re.findall(r"[^\s]{2,24}", text)
        total.update(tokens)
        for token in set(tokens):
            seen[token].add(row["page"])
    noise = sorted(t for t, pages in seen.items()
                   if len(pages) >= threshold and total[t] <= len(rows) * NOISE_PER_UNIT_MAX)

    name = os.path.splitext(os.path.basename(path))[0]
    if dump:
        write_dump(out_dir, name, rows, dumps, path, model)
    if render:
        render_units(path, out_dir, name, len(rows), dpi, browser)
    return name, rows, noise, baseline, full_bleed, model, frames


def render_dump(row, text, found):
    head = (f"<!-- {row['label']} | chars {row['chars']} | images {row['images']} "
            f"({row['images_noalt']} without alt) | math {row['math']['count']}"
            f"({row['math']['tex']} with TeX) | svg {row['svg']} | fragments {found.fragments} | "
            f"notes {row['notes_chars']} | hidden {row['hidden_by'] or 'none'} | "
            f"verdict {row['verdict']} | traps {','.join(row['traps']) or '—'} -->")
    title = first_line(text) or "(no heading)"
    body = [head, f"### {row['label']} — {title}", ""]
    if found.formula_markup:
        body += [f"> {found.formula_blocks} hand-built formula piece(s) here are assembled from "
                 f"spans, so the flattened text below does not carry them. Rebuild each formula "
                 f"from the markup here — never from the flattened line — and cite it "
                 f"`({row['label']}, rebuilt from markup)`.", "",
                 "**Formula markup**"]
        body += [f"- `{markup}`" for markup in found.formula_markup]
        body += [f"- description in words: {label}" for label in found.labels]
        body += [""]
    body += [text or "_(no extractable text)_"]
    if found.alts:
        body += ["", "**Images in this unit**"]
        body += [f"- `{src or '(no src)'}`" + (f" — alt: `{alt}`" if alt else " — no alt")
                 for src, alt in found.alts]
    if found.latex or found.math_nodes:
        body += ["", "**Formulas recovered from the markup**"]
        body += [f"- `${latex.strip()}`" for latex in found.latex if latex.strip()]
        body += [f"- `[mathml] {node['text']}`" for node in found.math_nodes
                 if not node["tex"] and node["text"]]
    if found.notes:
        body += ["", "**Speaker notes** (invisible to the audience; mine it, never cite it as "
                     "slide text)"]
        body += ["", collapse(" ".join(found.notes))]
    if found.hidden:
        body += ["", "**Hidden text** (in the file, not on the screen — see `hidden_by`)"]
        body += ["", collapse(" ".join(found.hidden))]
    return "\n".join(body)


def first_line(text):
    """The unit's own heading, skipping an image alt line, which is a caption at best."""
    for line in text.split("\n"):
        line = line.strip()
        if line and not line.startswith("[img alt]") and not line.startswith("[frame src]"):
            return line[:90]
    return ""


def write_dump(out_dir, name, rows, dumps, path, model):
    header = [f"# {os.path.basename(path)} — extractable text, one block per unit", "",
              f"Page model: **{model}**, {len(rows)} unit(s). The unit numbering is this deck's "
              f"citation system: the third unit is `s03`.", ""]
    with open(os.path.join(out_dir, f"{name}.slides.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(header + dumps) + "\n")


def find_browser(explicit):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for name in ("msedge", "chrome", "chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                      r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                      r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                      "/usr/bin/chromium"):
        if os.path.isfile(candidate):
            return candidate
    return None


def render_units(path, out_dir, name, units, dpi, browser):
    """Best-effort: print the deck to PDF, then split it into one PNG per printed page.

    A deck whose print stylesheet does not put one slide on one page gives renders that do not line
    up with the ledger. That is reported rather than hidden, because a silently misaligned render
    is worse than none.
    """
    exe = find_browser(browser)
    if not exe:
        sys.stderr.write("no browser found: skipping renders (pass --browser PATH)\n")
        return
    try:
        import pymupdf
    except ImportError:
        sys.stderr.write("pymupdf not installed: skipping renders, the ledger still stands\n"
                         "    python -m pip install --quiet pymupdf\n")
        return
    tmp = tempfile.mkdtemp(prefix="triagehtml")
    pdf = os.path.join(tmp, "deck.pdf")
    url = "file:///" + os.path.abspath(path).replace("\\", "/")
    for attempt in range(1, 5):
        if os.path.exists(pdf):
            os.remove(pdf)
        try:
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-first-run",
                            f"--user-data-dir={os.path.join(tmp, f'p{attempt}')}",
                            "--no-pdf-header-footer", "--virtual-time-budget=8000",
                            f"--print-to-pdf={pdf}", url],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        except subprocess.SubprocessError:
            continue
        # The print is slow, not absent: Chromium's launcher can return before the file is
        # flushed, so wait for a non-empty file rather than checking once and retrying.
        for _ in range(30):
            if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
                break
            time.sleep(1)
        if os.path.exists(pdf) and os.path.getsize(pdf) > 0:
            break
    if not os.path.exists(pdf) or os.path.getsize(pdf) == 0:
        sys.stderr.write("the browser produced no PDF: no renders (the deck may need its own "
                         "build step, or its slides may be laid out by script)\n")
        return
    doc = pymupdf.open(pdf)
    for number, page in enumerate(doc, 1):
        page.get_pixmap(dpi=dpi).save(
            os.path.join(out_dir, "pages", f"{name}-s{number:02d}.png"))
    printed = doc.page_count
    note = "" if printed == units else (
        f"  [note] {units} ledger unit(s) vs {printed} printed page(s): the print stylesheet does "
        f"not put one slide on one page, so check a render against its ledger row before trusting "
        f"it")
    print(f"  renders: {printed} printed page(s) -> pages/{name}-sNN.png{note}")


def write_ledger(out_dir, name, rows, noise, sources, baseline, full_bleed, model, unit_word,
                 frames):
    os.makedirs(os.path.join(out_dir, "pages"), exist_ok=True)
    with open(os.path.join(out_dir, "ledger.json"), "w", encoding="utf-8") as fh:
        json.dump({"sources": sources, "master_noise": noise, "background_baseline": baseline,
                   "full_bleed": full_bleed, "unit": unit_word, "page_model": model,
                   "embedded_frames": frames, "pages": rows}, fh, ensure_ascii=False, indent=1)

    counts = collections.Counter(r["verdict"] for r in rows)
    trap_counts = collections.Counter(t for r in rows for t in r["traps"])
    title = {"slide": "Slide", "section": "Section", "document": "Document"}.get(unit_word,
                                                                                "Unit")
    lines = [f"# {title} ledger — {name}", "",
             f"{title}s **{len(rows)}** | readable {counts['readable']} | "
             f"needs-vision {counts['needs-vision']} | needs-human {counts['needs-human']}", "",
             f"> Page model: `{model}`. A unit here is what triage decided a page is, and the "
             f"ledger is this deck's citation map.", ""]
    if full_bleed:
        lines += [f"> This deck is **picture-led** (median image share {baseline}): per-unit image "
                  "share carries no signal, so every text-thin unit is flagged `thin-text` and "
                  "sent to the vision pass.", ""]
    if frames:
        lines += ["> This file **frames other files**. The ledger covers this file only: the "
                  "framed document's units are not rows here.", ""]
        for frame in frames:
            if frame["content"]:
                mark = "content"
            elif frame["hidden"]:
                mark = "hidden frame"
            elif not frame["exists"]:
                mark = "missing"
            else:
                mark = f"only {frame['bytes']} bytes"
            lines += [f"> - `{frame['src']}` → `{frame['path']}` ({mark})"]
    lines += ["| Trap | Units |", "|---|---|"]
    lines += [f"| {t} | {c} |" for t, c in sorted(trap_counts.items())] or ["| — | 0 |"]
    if noise:
        lines += ["", "**Master noise** (repeats across units; strip before analysis): "
                  + ", ".join(f"`{t}`" for t in noise)]
    lines += ["", f"| {title} | Chars | Image share | Traps | Verdict | Detail |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        detail = []
        if r["notes_chars"]:
            detail.append(f"{r['notes_chars']} chars of speaker notes")
        if r["hidden_by"]:
            detail.append(f"hidden: {r['hidden_by']}")
        if r["math"]["count"] or r["math"]["tex"] or r["math"]["image"]:
            detail.append(f"math {r['math']['count']} ({r['math']['tex']} with TeX source) + "
                          f"{r['math']['image']} image(s)")
        if r["formula_blocks"]:
            detail.append(f"{r['formula_blocks']} formula piece(s), {r['labels']} described in "
                          f"words")
        if r["svg"]:
            detail.append(f"{r['svg']} content svg(s)")
        if r["frames"]:
            detail.append(f"{r['frames']} frame(s)")
        if r["fragments"]:
            detail.append(f"{r['fragments']} fragment(s)")
        if r["images"]:
            detail.append(f"{r['images']} image(s), {r['images_noalt']} without alt")
        lines.append("| {label} | {chars} | {raster} | {traps} | {verdict} | {detail} |".format(
            label=r["label"], chars=r["chars"], raster=r["raster"],
            traps=",".join(r["traps"]) or "—", verdict=r["verdict"],
            detail="; ".join(detail) or "—"))
    with open(os.path.join(out_dir, "ledger.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return counts


def merge_sources(out_dir, entries):
    """Add this run's files to <out>/sources.json without dropping another format's rows."""
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
    ap = argparse.ArgumentParser(description="easy-learning HTML courseware triage")
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", default="notes")
    ap.add_argument("--slide-selector", default=None,
                    help="force the unit element, e.g. 'section.slide' or '.marp-slide'")
    ap.add_argument("--render", action="store_true",
                    help="print the deck with headless Chromium and split it into PNGs")
    ap.add_argument("--browser", default=None, help="path to a Chromium-family browser")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--no-dump", action="store_true")
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
            name, rows, noise, baseline, full_bleed, model, frames = triage_html(
                path, out_dir, not args.no_dump, args.render, args.dpi, args.slide_selector,
                args.browser)
        except (ValueError, OSError, UnicodeError) as exc:
            sys.stderr.write(f"could not read {path}: {exc}\n")
            return 2
        unit_word = unit_word_for(model)
        counts = write_ledger(out_dir, name, rows, noise, [os.path.abspath(path)], baseline,
                              full_bleed, model, unit_word, frames)
        sources.append({"file": os.path.abspath(path), "format": "html", "pages": len(rows),
                        "unit": unit_word, "page_model": model, "full_bleed": full_bleed,
                        "verdicts": dict(counts),
                        "ledger": os.path.join(out_dir, "ledger.md"),
                        "slides": os.path.join(out_dir, f"{name}.slides.md")})
        print(f"{os.path.basename(path)}: {len(rows)} {unit_word}(s) via {model} | "
              f"readable {counts['readable']} | needs-vision {counts['needs-vision']} | "
              f"needs-human {counts['needs-human']}"
              f"{' | picture-led' if full_bleed else ''}")
        print(f"  ledger  -> {os.path.join(out_dir, 'ledger.md')}")
        print(f"  text    -> {os.path.join(out_dir, name + '.slides.md')}")
        for frame in frames:
            if frame["content"]:
                print(f"  framed  -> {frame['path']}  (triage this file too: the ledger above "
                      f"does not cover it)")

    merge_sources(args.out, sources)
    return 0


if __name__ == "__main__":
    sys.exit(main())
