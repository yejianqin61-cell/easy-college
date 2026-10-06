# Trap families

Courseware lies in a small number of ways. Each family below gives its **signature** (what the triage
script reports), its **recovery** (what to do instead of trusting the page), and **evidence** from
`example/CST204-ADT and searching.pdf` — a 76-page vector-typeset lecture that hit five of the six.

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

## Ledger schema

One row per page. `scripts/triage.py` fills the first group; steps 2–5 fill the rest.

| Column | Source | Values |
|---|---|---|
| `src` | script | input file name |
| `page` | script | 1-based page number |
| `chars` | script | extractable characters |
| `raster` | script | largest image coverage of the page, 0–1 |
| `traps` | script | `ghost-text`, `garbled-math`, `raster-only`, `thin-text`, `empty-text`, `duplicate`, `master-noise` |
| `verdict` | script | `readable` / `needs-vision` / `needs-human` |
| `cut` | step 2 | `keep` / `drop` |
| `reason` | step 2 | `R1-motivation` … `R5-admin` |
| `module` | step 3 | which module consumed the page |
| `note` | steps 3–4 | correction, rebuild, or `no-content` reason |

A page is `needs-human` when `ghost-text` is present (the script cannot tell which of the two overlapping
tokens is real) or when a contradiction is found by hand. `needs-vision` covers `garbled-math`,
`raster-only`, `thin-text` and `empty-text`. `duplicate` alone keeps the page `readable` — the cut
decision, not the verdict, is what removes it.

The triage script also records `background_baseline` and `full_bleed` at document level; when
`full_bleed` is true, per-page `raster` values are meaningless and `thin-text` is the live signal.
