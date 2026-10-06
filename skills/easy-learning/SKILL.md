---
name: easy-learning
description: >
  Turn uploaded courseware into study notes: a per-page triage ledger, a Markdown of knowledge
  points interleaved with the lecture's own self-test questions, a PDF, and an honest report of the
  pages that were unreadable and the pages that were dropped as background.

  Use when the user uploads 课件/讲义/PPT/slides/PDF and wants notes out of them: 整理成笔记, 提炼知识点,
  提取课件试题, 课件转笔记, 讲义总结, 划重点, 期末复习资料, 考前突击, "make notes from these slides",
  "extract the key points", "pull the quiz questions", "turn this lecture into notes".
  Also when another skill needs a lecture mined for knowledge points or self-test items.

  Don't use for a raw text dump with no structure, for a single-page file, or when the user only wants
  one question answered about a file's contents.
license: MIT
compatibility: Python (pymupdf, installed on first run) for PDF triage; pandoc plus Edge/Chrome for PDF output.
metadata:
  author: easy-learning contributors
  version: 0.2.0
  category: document-creation
  pattern: pipeline
  tags: [courseware, notes, pdf, pptx, docx, knowledge-extraction, quiz, study, provenance]
---

# easy-learning

**Every page gets a verdict; every item gets a page number.**

A lecture lands as a file; a set of study notes leaves. Two invariants run through every step below.

**Every page gets a verdict.** An un-judged page is the failure this skill exists to prevent, so each
page of each input lands in the **ledger**: one row holding that page's verdict, its trap, its keep/drop
decision, its reason code, and the module it fed. Triage writes the ledger, cutting annotates it, the
notes cite it, and the final report is its two tails. The ledger reconciles at every step —
**rows = the sum of all input page counts**.

**Every item gets a page number.** No knowledge point, formula, table, question or correction enters the
notes without the source page it came from. A reader must be able to open the original lecture at the
cited page and find that content there. This is what makes the notes checkable instead of merely
plausible, and it is not optional formatting.

Outputs land in `./notes/<input-name>/`:

| File | Holds | Read by |
|---|---|---|
| `ledger.md` | per-page verdict + trap + keep/drop + reason | the user, step 7 |
| `ledger.json` | the same, machine-readable | steps 2–5 |
| `<name>.notes.md` | the notes: modules, knowledge points, questions | the user |
| `<name>.notes.mindmap.svg` | the overview map, generated from the notes' headings | embedded in the notes |
| `<name>.notes.pdf` | the deliverable | the user |
| `pages/pNN.png` | renders, for the vision pass and for the user to check | step 1, step 7 |

## Step 0 — Inventory and toolchain

List the files the user named — or, when they said "the files I uploaded", the attachments in this
session. Detect the format of each, then confirm an extractor **and** a renderer before reading
anything.

| Format | Extract | Render (for the vision pass) | Install if missing |
|---|---|---|---|
| `.pdf` | `pymupdf` (`scripts/triage.py`) | `pymupdf` page render | `python -m pip install --quiet pymupdf` |
| `.pptx` | `python-pptx` text + speaker notes | LibreOffice `--convert-to pdf`, then render | `python -m pip install --quiet python-pptx` |
| `.docx` | `pandoc -t gfm` | convert to PDF, then render | pandoc is usually already present |
| `.md` / `.txt` | read directly | none needed | — |

Install quietly, then **verify by opening one input and printing its page or slide count** — a
successful import is not evidence that the file parses.

Done when every input has a confirmed extractor and renderer, and its page/slide count has been
printed.

## Step 1 — Triage every page

Run `scripts/triage.py` over each PDF; for other formats walk the slides/paragraphs the same way. The
script emits the ledger and the page renders, and flags the **trap families** — text that is hidden,
garbled, rasterized, duplicated, or simply wrong. Read
[`references/traps.md`](references/traps.md) before writing any recovery logic; it holds each trap's
signature, its recovery, and a worked example.

Give every page exactly one verdict:

| Verdict | Meaning | Next |
|---|---|---|
| `readable` | the text layer carries the page | extract normally |
| `needs-vision` | the meaning lives in a formula or a bitmap | run the vision pass on the render |
| `needs-human` | the text layer lies (hidden tokens, contradictions) | resolve from the render, then log the correction |

A page whose content is a chart, a screenshot, or an equation is never `readable` just because the
text layer is non-empty.

Done when **every page of every input has exactly one verdict**, the row count equals the sum of the
input page counts, and every `needs-vision` / `needs-human` page names its trap and its recovery.

## Step 2 — Cut only the background

**Fidelity is the default.** A `keep` page is carried into the notes **in full** — every sentence of
body text, every formula, every table, every question. Curating is not condensing: you may reorganise,
you may not select. A page of plain prose about a concept is content, and all of it stays, even when it
reads as background-ish. Only background material may be dropped.

Annotate each row with `cut` (`keep` / `drop`) and a **reason code**. A page with no reason code stays
`keep` — dropping demands a code, not a feeling.

| Code | Drops | Examples |
|---|---|---|
| `R1-motivation` | background and motivation: why the topic matters, history, philosophy, "the need for X" | CST204 p2–p4, p8–p9 |
| `R2-analogy` | pure analogy: metaphor, everyday-life illustration, familiar-interface talk | CST204 p14–p15 |
| `R3-frame` | cover, section divider, agenda, thank-you — pages with no body text | CST204 p1, p19, p34 |
| `R4-repeat` | exact duplicates, or ≥0.85 token-identical repeats; adjacent animation frames | CST204 p38–p40, p50–p62 |
| `R5-admin` | breaks, attendance, logistics, external video links | CST204 p48, p73 |

There is deliberately no code for "this looked unimportant". A side technique, a general method, a wall
of prose about systematic error, a learning-outcomes slide — each is page content, and each is kept
whole. When in doubt, keep: over-dropping is the failure the user actually notices.

When a page is `drop` but still holds a usable example, table, or question, move that content into the
module that needs it **before** dropping the page.

Done when every row carries `cut` + reason code, every `drop` cites one of the five codes above, and
every dropped page is listed in step 7 so the user can veto it.

## Step 3 — Extract the knowledge

For each `keep` page, carry its content into the module that owns it. Three rules carry the quality:

- **Fidelity over brevity.** Every sentence of body text, every formula, and every table on a `keep`
  page reaches the notes. Reorder, group, and retitle freely; delete nothing. A concept page that reads
  as prose stays as prose.
- **Formulas are rebuilt, not copied.** A formula from a `needs-vision` page is re-derived from the
  rendered image and written as LaTeX; the text layer is only a pointer to where the formula sits.
- **Corrections are flagged, never silent.** When a page contradicts itself or the field's convention,
  write the corrected value and a one-line note with the page number. The lecture's error is itself
  exam-relevant.

Done when every `keep` page can be traced to its content in the notes — each one either carried, or
logged `no-content` with a reason (a pure question page, a table absorbed verbatim elsewhere) — and
every item in those notes carries its page citation.

## Step 4 — Collect the self-test questions

Sweep the `keep` pages for the lecture's own questions: in-class checks, "your turn" prompts, practice
items, discussion prompts, and end-of-lecture review questions. Each item records its source page, its
stem, its options, and its answer — or `unanswered`.

Unanswered questions are the most valuable output of this step: they are the lecture's own exam signal
and they cannot be found in any answer key. Mark them clearly rather than inventing an answer, and keep
the answer you do supply visually separate from the stem.

Done when every page the ledger marks as containing a question has at least one extracted item, and
every extracted item appears exactly once in the question set.

## Step 5 — Write the notes

Structure: `##` for a module, `###` for a knowledge point, numbered `N.M`. Knowledge and its questions
travel together — a question follows the knowledge point it tests.

**Open with a mind map.** The notes start with one picture of the whole lecture, generated from the
notes' own headings so it can never drift out of sync with them:

```bash
python scripts/mindmap.py "<out>/<name>.notes.md" --insert --alt "<caption, in the user's language>"
```

This draws a right-branching map — root → modules → knowledge points — as a standalone SVG and drops
the image reference just above the first module. Headings are the single source of truth: `#` is the
root, `##` a branch, `###` a leaf. A `##` section with no `###` children (appendices, errata, a
table of contents) is left out, because the map shows knowledge structure rather than the document's
furniture. Re-run it after any heading change; `--insert` refreshes the reference instead of adding a
second one. Pass `--accent` to override the palette if a deck needs different colours.

An SVG is the only mind-map format that survives this pipeline: Mermaid needs a CDN or a ~300 MB
`mermaid-cli`, Graphviz and PlantUML need extra binaries, and ASCII art breaks on CJK because Chinese
glyphs are double-width. SVG is vector, offline, dependency-free, and printed crisp.

**Language.** The notes follow the language the user asked in:

- **Chinese prompt → Chinese notes, bilingual terms, English verbatim.** Write the body in Chinese, and
  on first use give every technical term in both languages: the Chinese term, then the English term in
  full-width parentheses with no space before the opening parenthesis. The lecture's own wording,
  definitions and question stems stay in the original English, set apart in blockquotes or quotes from
  your Chinese narration. Never translate a term away — the student's exam paper will use one of the two.
- **English prompt → English throughout**, including headings and question blocks, with no Chinese gloss.

Every sample and template in this skill is written in English. Render them in the user's language,
preserving the structure and the citation suffix.

Layout rules — each changes the output, so none is decoration:

- **A table only when ≥3 rows share ≥2 attributes** (comparisons, parameter lists, complexity tables).
  Otherwise a list.
- **Bold two things only**: the term being defined, and the exam-critical number. Never a whole
  sentence.
- **Every knowledge point and every question ends with its source page** — `(p42)`, or
  `(p42, rebuilt from image)` when the value came from the render rather than the text layer.
- Formulas are inline LaTeX — `$O(\log n)$`, `$T(n) = an + b$`.
- Questions render as a marked line plus an indented quote for the answer. The answer is a **nested**
  blockquote — `> >` with the space, and a blank `>` line between them — otherwise the `>` prints as
  literal text:

```markdown
### 4.2 The exact cost of sequential search

A match at index $j$ costs $j+1$ key comparisons; an absent target costs $n$. (p42)

| Case | Comparisons | Cost |
|---|---|---|
| Successful, best | 1 | $\Theta(1)$ |
| Unsuccessful | $n$ | $\Theta(n)$ |

> ❓ **Check yourself**: in `[12, 5, 19, 8, 22, 3]`, how many comparisons does a search for 8 take? (p46)
>
> > Answer: index 3, four comparisons. (p47)
```

Done when the file is on disk, every `keep` page's knowledge appears in exactly one module, every
extracted question is placed exactly once, no `unanswered` item is silently missing, and every item
carries a page citation.

## Step 6 — Render the PDF

Pandoc builds self-contained HTML with native MathML (renders offline in Chromium — no CDN), then
headless Chromium prints it. **Build from a space-free temp directory holding the notes and every
asset they reference, with an isolated browser profile:**

```powershell
# the notes reference the mind map by relative path, so it must travel with them
Copy-Item "<out>\<name>.notes.md","<out>\<name>.notes.mindmap.svg" "<tmp>\"

pandoc "<tmp>\<name>.notes.md" -s --mathml --embed-resources `
  --metadata title="<title, in the user's language>" -c "<skill>\assets\notes.css" `
  -o "<tmp>\notes.html"

& "<edge-or-chrome>" --headless=new --disable-gpu --no-first-run `
  --user-data-dir="<tmp>\chromeprofile" `
  --no-pdf-header-footer --print-to-pdf="<tmp>\notes.pdf" "file:///<tmp>/notes.html"
# then copy <tmp>\notes.pdf to the output folder
```

Three failure modes this avoids, all observed in practice: an **already-running** browser absorbs the
invocation so `--print-to-pdf` silently writes nothing (hence `--user-data-dir`), a `file:///` URL
containing spaces or parentheses does not resolve (hence the temp directory), and a relative image
path breaks when the notes are built from somewhere other than their own folder. A print can also lose
a race with profile creation and write nothing at all — if the PDF is missing, delete the profile
directory and run the browser once more before suspecting anything else. The step is not done until you
have confirmed the PDF file exists and is non-empty; a zero exit code proves neither.

`--embed-resources` inlines the SVG as a data URI and the stylesheet into the HTML, so the PDF is
self-contained and the mind map stays **vector** — its text is selectable and stays sharp at any zoom,
which a screenshot of a diagram would not be.

`assets/notes.css` sets A4 margins, a CJK font stack (`Microsoft YaHei` → `SimSun` → sans-serif),
bordered compact tables, `page-break-inside: avoid` on tables and code blocks, and hides pandoc's
injected `h1.title` so the page shows one title instead of two. `--mathml` is what keeps formulas
typeset with no network — MathJax/KaTeX would need a CDN. Fallbacks when headless Chromium is absent,
in order: LibreOffice `--convert-to pdf`, a `pip install xhtml2pdf` HTML→PDF pass, or hand the user the
HTML and say so.

Then **open the PDF and look at the mind map page, a table page, a formula page, and a page of the
user's language.** Check: page count > 0, the map is present and legible (not blank, not clipped), the
user's script is not tofu boxes, formulas are typeset rather than raw `$...$`, tables are not clipped at
the margin.

Done when the PDF exists, is non-empty, and that three-page spot check passed.

## Step 7 — Report and deliver

Present the PDF, then report in the reply itself — not only inside a file — the ledger's two tails:

1. **Unreadable pages** — every `needs-vision` and `needs-human` page, with the trap and what was lost
   or rebuilt.
2. **Dropped pages** — every `drop` page with its reason code and its one-line reason, so the user can
   veto any of them. A veto puts the page back into the notes as content.

Then reconcile out loud: `total = readable + needs-vision + needs-human`, `total = keep + drop`, and
state that every `keep` page has a landing place in the notes. Any assumption you made — a merge
decision, a corrected value, a page you could not judge — belongs in this report.

Done when both tails are listed, both equations balance against the input page totals, and the PDF has
been presented.
