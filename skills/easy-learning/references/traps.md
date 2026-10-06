# Trap families

Courseware lies in a small number of ways. Each family below gives its **signature** (what the triage
script reports), its **recovery** (what to do instead of trusting the page), and **evidence** from
`example/CST204-ADT and searching.pdf` — a 76-page vector-typeset lecture that hit five of them.

The **HTML decks** part, after these seven, covers the tells only markup has — hidden material,
hand-built formulas, script-built slides, content in a framed file — with evidence from
*Electric Field Lab (Katz)*, a 700 KB single-file HTML lab guide, and from a PDF's own reveal.js
export, so a reader can see both formats measured rather than asserted.

---

## 1. Hidden text — `ghost-text`

**Signature.** Two spans of a page overlap by more than ~45% of the smaller one. One of them is painted
over by a filled shape drawn later, so it is **invisible on the rendered page but present in the text
layer**.

**Recovery.** Both candidates are extracted; keep the one that fits the neighbouring pages' pattern and
the domain's own logic. Never let a duplicate token into a table or a question stem.

**Evidence.** CST204 p38–p40 and p50–p62 (16 pages) each carry two dark `34` tokens hidden underneath
the blue array cells. Text-layer extraction of "the array" yields 19 values instead of 15:

```
text layer: 34 34 1 3 30 36 39 40 42 34 34 49 53 61 75 76 86 97 99
actual:        1 3 30 36 39 40 42 49 53 61 75 76 86 97 99
```

A pipeline that trusts the text layer emits a worksheet asking where `34` sits — an array that does
not exist. This is the single highest-value check in the skill.

## 2. Garbled math — `garbled-math`

**Signature.** Characters in the Arabic, Syriac, Devanagari, or Private Use areas (`U+0600–U+0DFF`,
`U+E000–U+F8FF`) appear in a page that is otherwise Latin. Caused by an embedded math font with no
`ToUnicode` map.

**Recovery.** Treat the whole formula as `needs-vision`: render the page at ≥200 dpi and read the
formula from the image, then write it as LaTeX. The text layer is used only to locate it.

**Evidence.** CST204 has 13 such pages (p21, p30–p33, p35, p42–p46, p66, p67). Measured mapping:

| Real | Extracted | Real | Extracted | Real | Extracted |
|---|---|---|---|---|---|
| `n` | `݊` `࢔` | `1` | `૚` | `O` | `ܱ` |
| `2` | `૛` | `k` | `݇` `࢑` | `Θ` | `ࡻ` |
| `a` | `ܽ` | `b` | `ܾ` | `T` | `ܶ` |
| `j` | `݆` `࢐` | `i` | `࢏` | `K` | `ܭ` |

`T(n) = an + b` (p44) extracts as `ܶ(݊) = ܽ݊ + ܾ`.

## 3. Raster-only content — `raster-only`

**Signature.** An embedded image covers more than ~8% of the page area, and the page's extractable text
is thin (under ~120 characters).

**Recovery.** `needs-vision`: render at ≥200 dpi, read the content visually, and tag every value taken
from the image as rebuilt from the image in the notes. A chart's numbers are read from the image, never
guessed from the caption.

**Evidence.** CST204 p36 (two animation screenshots, 28% of the page, 29 chars of text), p75 (a
1037×448 line chart, 37% of the page, 50 chars), p71 (a 1511×346 array table plus hand-drawn arrows
that do not align with the cells — and only four arrows against an answer of five). p75 also shows why
charts need judgement: it draws `O(log n)` as a rising line, contradicting the lecture's own
conclusion, so its values should not be quoted as complexity evidence.

## 4. Duplicate frames — `duplicate`

**Signature.** A page's token set overlaps the previous page's by ≥0.85; at 1.0 with an identical
string the two pages are exact duplicates.

**Recovery.** Keep the first frame and the summary frame, drop the rest under `R4-frame-repeat`. A pure
build sequence usually ends in one page that states the whole trace — prefer that one.

**Evidence.** CST204 p54 = p55 and p58 = p59 are exact duplicates; p38/p39/p40 reach 0.97–1.0; the
13-page p50–p62 run is one binary-search animation, already summarised by p49 (three-step diagram) and
p63 (the same trace as a table).

## 5. Author errors — `author-error`

**Signature.** No geometric tell. Detection is a **contradiction**: the page disagrees with itself,
with another page, or with the field's convention.

**Recovery.** Correct the value in the notes and flag it in the source page's line. Do not propagate the
error, and do not silently fix it — the discrepancy is often the most exam-relevant thing on the page.

**Evidence.** CST204 drops a minus sign in five places: p22 ("or **1** when the target is absent"),
p37 and p64 (`return 1;` in the C listings, where the contract is `-1`), p42 (`Status: 0 = found;
1 = absent`), p47 ("Target 7: return 1 after 6 comparisons"). Page p35 shows a correct `Absent: −1`
and p64 renders `high = mid - 1` correctly, which proves the loss is authoring, not rendering.
A second contradiction: p37 returns the match index while p42 returns a `0/1` status code for the same
function — two contracts, one algorithm.

## 6. Master noise — `master-noise`

**Signature.** A short token appears on ≥90% of pages (footer, running title, slide number), or the same
image is embedded on every page (logo, background).

**Recovery.** Strip it from the extracted text before analysis, and exclude it from similarity scoring
so it does not inflate duplicate ratios.

**Evidence.** CST204 carries the footer `Data Structure` on all 76 pages and the same 406×106 university
logo image on every page — 76 repetitions of two tokens that belong to no knowledge point.

## 7. Full-bleed raster deck — `thin-text` / `empty-text`

**Signature.** The document's **median** image coverage is high (≈1.0), because every slide is one
full-page background bitmap (a blackboard, a template, a screenshot-of-a-slide). Per-page coverage then
carries *no* information, and a coverage threshold fires on dividers and "Thank you" slides.

**Recovery.** When the median coverage exceeds ~0.5, stop using coverage as a per-page signal and
switch to **text density** instead: flag every page under ~120 extractable characters as `thin-text`
(0 characters as `empty-text`) and send it to the vision pass. The verdict is "look at this render",
not "the content is in the image" — only the render tells you which.

**Evidence.** GPL Error Analysis (52 pages) is full-bleed: coverage is 1.0 on all 52 pages. A
coverage-based rule mislabelled the cover, the three part dividers and the closing slide as
`raster-only`, while the pages that really needed eyes — p13 (Arithmetic Operations, **whole page is a
screenshot**, 22 chars), p39 (four propagation formulas, **0 chars**), p47 (a designed table,
**0 chars**), p46 (a data table plus a fitted graph, 28 chars) — look identical to dividers under any
coverage threshold. Only text density plus a look at the render separates them.

The same run also showed the ghost-text rule's common false positive: a variable set into a sentence's
whitespace gap ("A physical quantity **f** is a function of …") or a combining accent over its base
glyph overlaps its neighbour by >0.45 while being perfectly visible. The triage script now ignores a
span that sits entirely inside another span's glyph-free gaps; genuine hidden text (CST204's `34` inside
a filled cell) still reports.


---

# HTML decks

An HTML deck lies differently from a PDF, because there is no text layer to lie about: the markup
*is* the source. What changes is that the page has to be defined at all, and that content can be in
the file while being invisible on the screen.

## What counts as a page

The file has no pages, so `scripts/triage-html.py` decides, and says so. The ladder, in order:

1. **`marked-slides`** — an element carries a slide class (`slide`, `slides`, `marp-slide`,
   `remark-slide`, `step`, `page`, `shower`) or a slide attribute (`data-slide`, `data-index`,
   `data-marpit-svg`, `data-step`). A container holding them (`.slides`) is looked through, and a
   wrapper `<section>` holding only `<section>`s is a vertical stack whose children are the slides.
2. **`sections`** — `<section>` elements: reveal.js, Quarto, and any hand-written page that uses
   semantic sections.
3. **`sibling-<tag>`** — the largest run of same-tag siblings holding the file's text. Prose tags
   (`p`, `li`, `td`, `pre`, `blockquote`) are never units: three `<p>` siblings are a paragraph, not
   three pages.
4. **`heading-<tag>`** — the document sliced at its top-level headings: one unit per heading and the
   content that follows it. This is the page model for a course reading rather than a deck.
5. **`single-document`** — one unit, honestly labelled. A deck that lands here is a detection
   failure, not a deck with one slide, and `--slide-selector "section.slide"` is the fix.

The model and the count are printed and stored as `page_model` / `unit` in `ledger.json`; the units
are the citation system (`s01`, `s02`, …) for that deck.

## 8. Hidden material — `hidden-content` / `hidden-slide`

**Signature.** A unit, or something inside it, carries `hidden`, `display:none` (inline or in a
stylesheet rule with a class/id selector from the short list `hidden`, `invisible`, `display-none`,
`d-none`, `answer`, `solution`, `secret`), a `visibility:hidden` style, a `class="hidden"`, or sits
inside `<template>`. The text is in the file and not on the screen.

**Recovery.** `needs-human`: read it, decide whether it belongs to the lecture, and carry it if it
does. Hidden material in courseware is disproportionately valuable — an answer key, a model answer, a
control panel that appears only for one geometry, a backup slide with the part of the derivation the
lecturer skips when time runs short.

**False positives, both measured.**

- **`aria-hidden="true"` is not hidden.** It hides content from a *screen reader*, not from the
  screen; decorative icons and duplicate captions carry it everywhere. Triage ignores it. Honouring
  it flagged 12 of the 15 units of one real deck.
- **An empty placeholder hides nothing.** `<div class="feedback" hidden=""></div>` is how a page
  reserves room for a script. A row is flagged only when the hidden subtree actually holds text or an
  image. This was the other 12-unit false positive on the same deck.
- **Fragments are not hidden.** `class="fragment"` is content the framework reveals on the next
  click; it is exempt, and treated as a build step instead (below).

**Evidence.** *Electric Field Lab (Katz)* — an HTML lab guide, 15 units, one `needs-human`:
`<div class="field" id="lcAngF" hidden="">` holds the *Arc angle, 2φ* control that appears only when
the reader picks the arc geometry. Nothing is lost, but the notes must not present the default
geometry as the only one.

## 9. Hand-built formulas — `formula-markup`

**Signature.** A formula assembled from spans with classes like `frac`, `sqrt`, `vec`, `overset`,
`equation`, `formula`. The text layer flattens it: a fraction extracts as its numerator glued to its
denominator.

**Recovery.** The dump prints the block's **markup**, which is exact, and any `aria-label` / `title`
on it, which is often the formula in words. Rebuild from that and cite
`(s12, rebuilt from markup)`. **Never quote the flattened line** — in the evidence below it reads
`E = FEqtestEq. 2.4 · unit N/C`, which is not a formula.

**Evidence.** *Electric Field Lab (Katz)* s01:

```html
<div class="eq eq-hero" aria-label="E vector equals F E vector divided by q test">
  <i class="vec">E</i> = <span class="frac"><span><i class="vec">F</i><sub>E</sub></span><span><i>q</i><sub>test</sub></span></span>
</div>
```

`\vec{E} = \vec{F}_E / q_{\text{test}}` — three lines of markup, invisible to a text pass.

## 10. Math that is in the markup — `math-source`

**Signature.** `<math>` (MathML) and/or `<annotation encoding="application/x-tex">`, or
`<script type="math/tex">`. The visible glyphs are produced by a script, but the source survives in
the file.

**Recovery.** `readable`, and better than a render: use the annotation's LaTeX verbatim. The dump
lists each recovered expression; where MathML has no TeX annotation it prints a linear approximation
marked `[mathml]`, which is a pointer to re-read the markup, not a formula to copy.

## 11. Pictures and diagrams — `image-only` / `image-alt` / `math-image` / `svg-only`

**Signature.** A unit under ~120 characters of text that holds an `<img>`, or a content SVG (not
`aria-hidden`, not inside a button or link) with no text around it. `math-image` when the image is a
formula (`class`/`src`/`alt` mentions math, equation, formula, katex, latex, or the `alt` is itself
LaTeX).

**Recovery.** `needs-vision` for `image-only`, `math-image` and `svg-only`: read the render, and cite
`(s12, rebuilt from image)`. Where the picture carries a real description in `alt`, the unit is
`image-alt` and `readable`, with the citation suffix `(s12, from alt text)`. The dump lists every
image with its `alt` — or says `no alt`, which is the finding.

**Picture-led decks.** As with PDFs, a deck whose *median* image share exceeds ~0.5 makes the
per-unit share useless: coverage stops being a signal, every text-thin unit is flagged `thin-text`
(0 characters: `empty-text`), and the render is the only judge. A five-slide deck of full-page
screenshots is the measured case.

## 12. Slides built by script — `js-rendered`

**Signature.** A unit under ~120 characters of text, no images, the document has `<script>`, and the
unit is either empty or holds a placeholder element (an empty `<div>`/`<canvas>`/`<figure>` with an
`id` or `class`). The text is not in the file at all.

**Recovery.** `needs-vision`: render `--render`, and if the browser prints an empty deck the source
was a dev-server build (Slidev, a Vue/React deck, an unbuilt Marp file). Ask for the built HTML, the
export, or the PDF — no amount of reading the file will produce text that is not there.

**Evidence.** A saved Claude artifact page (392 KB) is exactly this: its own body carries the shell
(toolbar, title, buttons), the courseware lives in a framed sibling file, and its `Electric Field
Lab (Katz).html` row is a 270-character `frame-shell`.

## 13. Content in a framed file — `frame-shell`

**Signature.** The unit is under ~1000 characters of its own text and contains an `<iframe>` /
`<frame>` with a **local, non-hidden** `src` that exists on disk.

**Recovery.** `needs-human`, and the fix is one command: the ledger lists the frame target and stdout
prints its path — **triage that file too** and count both ledgers as the one input. Rows cover the
files you actually read; a report that says otherwise is wrong.

Two filters are load-bearing, both measured on the same page: a *warm-up* frame (258 bytes,
`hidden`) and a *tracking* frame (`visibility:hidden`, 506 bytes) sit next to the 701 KB content
frame, and a rule that follows any `src` sends the reader to the wrong file. Frames that are hidden,
missing, or under ~1 KB are listed but marked, not followed.

## 14. Speaker notes, build steps, duplicates — `speaker-notes` / `fragments` / `duplicate`

- **`speaker-notes`** — `<aside class="notes">`, `.notes`, `.speaker-notes`. Invisible to the
  audience, often holding the answer. Mine it; never cite it as slide text. The plural matters:
  `class="note"` is a *visible* callout box in most handouts and matching it turns body text into a
  private channel — 41 units' worth on one real file.
- **`fragments`** — `.fragment` / `data-fragment-index` / `<details>`. The content arrives on a
  click, so it is content. It is also why a build sequence lands in the ledger: three frames of one
  derivation look like duplicates to a token-overlap rule.
- **`duplicate`** — the same rule as PDFs (≥0.85 token overlap with the previous unit), with the same
  caveat: it is the cut decision, not the verdict, that removes a page.

## Master noise in HTML

The PDF rule (a short token on ≥90% of pages) is too loose here, because a real deck's *vocabulary*
appears on every page too: `the`, `charge`, `field`. The HTML rule adds an occurrence rate —
furniture repeats about **once per unit**, so a token qualifies only if it appears on ≥90% of units
and at most ~1.5 times per unit. On the real lab guide that leaves `about` and `prompt`, the two
words of its per-section toolbar, and drops every content word.

---

## Ledger schema

One row per page. `scripts/triage.py` fills the first group; steps 2–5 fill the rest.

| Column | Source | Values |
|---|---|---|
| `src` | script | input file name |
| `page` | script | 1-based page number |
| `label` | HTML script | the unit's citation label, `s01` … (`page` is its number) |
| `chars` | script | extractable characters |
| `raster` | script | PDF: largest image coverage of the page, 0–1. HTML: the image share of the unit's content blocks |
| `traps` | script | PDF: `ghost-text`, `garbled-math`, `raster-only`, `thin-text`, `empty-text`, `duplicate`, `master-noise`. HTML: `hidden-content`, `hidden-slide`, `frame-shell`, `js-rendered`, `image-only`, `image-alt`, `math-image`, `svg-only`, `formula-markup`, `math-source`, `fragments`, `speaker-notes`, `duplicate`, `thin-text`, `empty-text` |
| `verdict` | script | `readable` / `needs-vision` / `needs-human` |
| `images`, `images_noalt`, `alt_chars` | HTML script | pictures, how many of them have no `alt`, and how much `alt` text the unit carries |
| `math` | HTML script | `count` (MathML blocks), `tex` (with a TeX source), `mathml_only`, `image` (formulas that are pictures) |
| `formula_blocks`, `labels` | HTML script | hand-built formula markup, and how many carry a description in words |
| `svg`, `frames`, `fragments` | HTML script | content SVGs, local frames, click-to-reveal fragments |
| `notes_chars` | HTML script | characters of speaker notes (mined, never cited as slide text) |
| `hidden_by` | HTML script | `self` / `descendant` — what made the unit or its content invisible |
| `cut` | step 2 | `keep` / `drop` |
| `reason` | step 2 | `R1-motivation` … `R5-admin` |
| `module` | step 3 | which module consumed the page |
| `note` | steps 3–4 | correction, rebuild, or `no-content` reason |

Document level: `background_baseline` and `full_bleed` for both formats; `unit`
(`page` / `slide` / `section` / `document`) and `page_model` for HTML; `embedded_frames` for HTML,
one entry per local frame with `exists`, `bytes`, `hidden` and `content` — only a `content` frame is
worth triaging.

A page is `needs-human` when `ghost-text` is present (the script cannot tell which of the two overlapping
tokens is real), when a contradiction is found by hand, or — in HTML — when `hidden-content`,
`hidden-slide` or `frame-shell` fires. `needs-vision` covers `garbled-math`, `raster-only`,
`thin-text`, `empty-text`, and in HTML `js-rendered`, `image-only`, `math-image` and `svg-only`.
`duplicate` alone keeps the page `readable` — the cut decision, not the verdict, is what removes it.
`formula-markup`, `math-source`, `image-alt`, `fragments` and `speaker-notes` are recoverable, so
they keep the unit `readable`; the recovery is in the dump, and the citation says which one was used.

Citations follow the unit: `(p42)` for a PDF, `(s03)` for an HTML unit, `(s03, rebuilt from markup)`
or `(s03, from alt text)` when the value came from the markup or the picture's description rather
than from the slide's own text.

The triage scripts also record `background_baseline` and `full_bleed` at document level; when
`full_bleed` is true, per-page `raster` values are meaningless and `thin-text` is the live signal.
