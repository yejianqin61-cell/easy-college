---
name: easy-review
description: "Turn courseware into revision notes: a knowledge map at the top, the lecture's knowledge points extracted completely and structured under modules as scannable items, and every exercise pulled out of the body into one self-test column at the end. Use for revision rather than first-pass learning: 复习笔记, 复习资料, 考前复习, 期末复习, 二轮复习, 知识梳理, 考点整理, 结构化笔记, 自测题汇总, 错题自测, \"revision notes\", \"make revision notes from these slides\", \"consolidate this lecture for the exam\", \"put all the questions at the end\", \"I already studied this, help me revise\". The source is always the lecture: the same courseware, read again for a different output shape. For first-time notes that interleave the lecture's questions with the material they test, use easy-learning instead. Don't use with no lecture to read, for a single-page file, or when the user only wants one question answered about a file's contents."
---

# easy-review

**A revision note is a different document from a first-pass note, not a shorter one.**

Four rules make it that document, and every step below serves them.

**1. It opens with the map.** The first thing after the title is one picture of the whole
lecture. A revision reader arrives knowing the material is familiar and needing to know where
they are in it; the map answers that before a single line of prose is read.

**2. Knowledge is extracted completely, as items.** The body is a *complete* itemised sweep:
every knowledge point of every kept page, one item per point, numbered, under the module that
owns it. This is the sharpest difference from first-pass notes. There, prose is carried over
whole; here, each point is **decided** — a definition, a list of rules, a comparison table, a
procedure, a formula — and written as something a reader can check off. Rewriting prose into
items is the job. Dropping a point is not.

**3. No question appears in the body.** Every exercise the lecture contains — in-class checks,
"pause the video" prompts, practice sets, discussion questions, end-of-lecture review items —
is extracted and moved to the end. A revision reader who hits a question mid-body either
answers it (and derails) or skips it (and trains themselves to skip). Neither is revision.

**4. The self-test column is last and is everything.** One section, at the very end, holding
every question the lecture asks, each with its stem and its answer, each cited to the page it
came from. It is both the revision aid and the coverage proof: the questions are the lecture's
own statement of what matters.

Two invariants carry over from the same source material, unchanged:

**Every page gets a verdict.** Each page of each input lands in the ledger — verdict, trap,
keep/drop, reason code, and the module it fed. The ledger reconciles at every step: **rows =
the sum of all input page counts.**

**Every item gets a page number.** No knowledge point, formula, table, question or correction
enters the notes without its source page, so any line can be checked against the original.

Outputs land in `./notes/<input-name>/`:

| File | Holds | Read by |
|---|---|---|
| `ledger.md` / `ledger.json` | per-page verdict + trap + keep/drop + reason | the user, step 7 |
| `<name>.review.md` | the revision note: map, modules, items, self-test column | the user |
| `<name>.review.mindmap.svg` | the knowledge map, generated from the note's own headings | embedded at the top |
| `<name>.review.pdf` | the deliverable, if the renderer is available | the user |
| `pages/pNN.png` | renders, for the vision pass and for the user to check | step 1, step 7 |

If the session also produced first-pass notes, keep both: study from `easy-learning`'s notes,
revise from these. Same folder, different stems, no collision.

## Step 0 — Inventory and toolchain

List the files the user named — or, when they said "the files I uploaded", the attachments in
this session. Detect each format, then confirm an extractor **and** a renderer before reading.

| Format | Extract | Render (for the vision pass) | Install if missing |
|---|---|---|---|
| `.pdf` | `pymupdf` (`scripts/triage.py`) | `pymupdf` page render | `python -m pip install --quiet pymupdf` |
| `.pptx` | `python-pptx` text + speaker notes | LibreOffice `--convert-to pdf`, then render | `python -m pip install --quiet python-pptx` |
| `.docx` | `pandoc -t gfm` | convert to PDF, then render | pandoc is usually already present |
| `.md` / `.txt` | read directly | none needed | — |

**Which source to read.** If this session already triaged the same lecture, reuse the renders and
the ledger — re-reading 76 pages to produce the same verdicts is waste. If it did not, triage
from scratch: `scripts/triage.py` here is the same script the `easy-learning` skill ships, so
the two agree page for page when a session uses both.

```
scripts/triage.py          per-page ledger + renders
references/traps.md        trap signature → recovery
```

This skill is self-contained on purpose: its folder is the unit that gets installed, and nothing
in it reaches into a sibling skill's files. If `pymupdf` cannot be installed, the two things you
lose are **the page renders** and **the trap signatures** — say so, extract with a plain
`pymupdf` text pass, and mark the ledger lower-confidence rather than pretending the traps were
checked.

Install quietly, then **verify by opening one input and printing its page or slide count** — a
successful import is not evidence that the file parses.

**Windows PowerShell 5.1 mangles non-ASCII arguments** passed to `python` or `pandoc`: it encodes
the command line in the ANSI code page, so `--root "知识结构图"` arrives as mojibake and argparse
reports `unrecognized arguments`. Set the encoding once per session, before the first call that
carries a Chinese or accented argument — or run the steps under PowerShell 7, which is UTF-8 by
default:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
```

This affects arguments only. File contents are unaffected as long as every script here reads and
writes UTF-8, which they do.

Done when every input has a confirmed extractor and renderer, its page/slide count has been
printed, and it is settled whether this is a fresh triage or a reused ledger.

## Step 1 — Triage every page

Run the ledger exactly as `easy-learning` step 1 does, and read
[`references/traps.md`](references/traps.md) before writing any recovery logic. Each page gets
one verdict:

| Verdict | Meaning | Next |
|---|---|---|
| `readable` | the text layer carries the page | extract normally |
| `needs-vision` | the meaning lives in a formula or a bitmap | run the vision pass on the render |
| `needs-human` | the text layer lies (hidden tokens, contradictions) | resolve from the render, then log the correction |

A page whose content is a chart, a screenshot, or an equation is never `readable` just because
the text layer is non-empty. This step is **not** optional for revision notes: revision is
where an error read off a bad text layer gets memorised as fact.

Done when every page of every input has exactly one verdict and the row count equals the sum of
the input page counts.

## Step 2 — Cut only the background

Identical to `easy-learning` step 2, and for the same reason: **fidelity is the default.** A
`keep` page is carried into the note in full. You may reorganise, retitle and re-itemise
freely; you may not select. Only background material may be dropped, each `drop` needs a reason
code, and each is listed in step 7 for the user to veto.

| Code | Drops | Examples |
|---|---|---|
| `R1-motivation` | background and motivation: why the topic matters, history, philosophy | "The Need for Data Structures" |
| `R2-analogy` | pure analogy: metaphor, everyday-life illustration | the find-a-student-ID story |
| `R3-frame` | cover, section divider, agenda, thank-you — pages with no body text | covers, "Part II" dividers |
| `R4-repeat` | exact duplicates, or ≥0.85 token-identical repeats; adjacent animation frames | 13 frames of one animation |
| `R5-admin` | breaks, attendance, logistics, external video links | "check on Moodle", break slides |

There is deliberately no code for "this looked unimportant". A side technique, a general method,
a wall of prose about systematic error, a learning-outcomes slide — each is page content and
each is kept whole. When in doubt, keep: over-dropping is the failure the user notices.

When a page is `drop` but holds a usable example, table or question, move that content into the
module that needs it **before** dropping the page.

Done when every row carries `cut` + reason code, every `drop` cites one of the five codes, and
every dropped page is listed in step 7.

## Step 3 — Extract the knowledge as items

This is where a revision note is made. Work through the `keep` pages and, for each, decide what
its knowledge *is*, then write it as items under the module that owns it.

**Itemising, not summarising.** These are the shapes a knowledge point takes; pick the one the
source supports and use it in this order of preference:

| Shape | Use when | Looks like |
|---|---|---|
| Definition | the page defines a term | the term in bold, then the lecture's own wording quoted, then the page |
| List of rules | a set of conditions, each with its own case | an item per rule, `Rule n` label kept verbatim |
| Comparison table | ≥3 things share ≥2 attributes | a table with one row per thing |
| Procedure | an ordered method, or a worked derivation | numbered steps, each step's formula written out |
| Formula block | a formula with named symbols | the formula in LaTeX, then a line per symbol |
| Pitfall / correction | the lecture contradicts itself | the value you should use, then what the source says |

**Nothing is dropped by itemising.** If a page holds five rules, five items appear. If a
paragraph holds three facts, three items appear. Rewriting a paragraph into three bullets is the
work; deleting the third bullet is not. The test of this step is the reverse of a summary's:
after reading, the user should hold everything the lecture taught, arranged so they can
interrogate it.

Structural rules:

- `##` — a module, matching the lecture's own parts where it has them, `## 模块 N｜…`.
- `###` — a knowledge point, numbered `N.M`, where `N` is the module's number.
- `####` — a sub-point, only when a knowledge point genuinely has parts (`Rule 1`–`Rule 4`).
  Never to nest a bullet list that a list would carry better.
- One page citation on **every** item — `(p42)`, or `(p42, rebuilt from image)` for a value read
  from a render rather than the text layer.
- Formulas are inline LaTeX: `$T^{2} = 4\pi^{2}L/g$`.
- Bold exactly two things, never a whole sentence: the **term being defined**, and the
  **exam-critical number**.
- A table only when ≥3 rows share ≥2 attributes. Otherwise a list.
- Corrections are flagged, never silent: the corrected value plus a one-line note and the page.
  The lecture's error is often the most exam-relevant thing on the page.

Done when every `keep` page is traceable to its content — each one either carried, or logged
`no-content` with a reason (a pure question page, a table absorbed verbatim elsewhere) — and
every item in the note carries its page citation.

## Step 4 — Collect the self-test material

Sweep the `keep` pages for the lecture's own questions: in-class checks, "your turn" and "pause
the video" prompts, practice items, discussion prompts, end-of-lecture review questions. Each
item records its source page, its stem, its options, and its answer — or `unanswered`.

Two things this step must do that a first-pass note need not:

- **Catch the questions embedded in prose.** A practice set is often a run-on line ("Pause the
  video and try the following exercises: 1) … 2) …") rather than a slide of its own. Miss it
  and the self-test column is short, which is the one defect the user will notice.
- **Keep the source's own numbering and wording.** The stems are what the lecture says; the
  student's exam will resemble them, not your paraphrase.

Unanswered questions are the most valuable items: they are the lecture's own exam signal and
cannot be found in any answer key. Mark them `unanswered` and never invent an answer. If you
supply a derived one, label it as derived and not from the lecture, as in
`补充（非课件内容，按 Rule 1–4 推得）`.

Also collect the **correction register** here: every place the source contradicts itself, its
answer key, or its own convention, with the page. It becomes a short table at the end of the
body — the one place a review note is allowed to editorialise, because a student revising from
a wrong answer key will memorise the wrong answer.

Done when every page the ledger marks as containing a question has at least one extracted item,
and every extracted item appears exactly once in the set.

## Step 5 — Write the revision note

Structure the file in exactly three parts, in this order:

```
# <title>                       the lecture, plus "复习笔记"
> source line                   lecture, term, page count
![知识结构图](<name>.review.mindmap.svg)      ← part 1: the map
## 模块 1｜…                    ← part 2: the body
### 1.1 …
## 复习自检｜原稿疑点与易错点      corrections + traps, if there are any
## 自测专栏 {#selftest}          ← part 3: every question
```

**Part 1 — the map.** Generate it from the note's own headings, so it can never drift out of
sync with the body:

```bash
python scripts/knowledge-map.py <out>/<name>.review.md \
  --root "<short root label, in the user's language>" \
  --alt "<caption, in the user's language>" --insert --before "模块 1"
```

`#` becomes the root, `##` a module, `###` a knowledge point, and a `###`'s `####` sub-points
hang beside it. Sections that are not knowledge (自测, 附录, 报告) are skipped, so the map shows
knowledge structure rather than the document's furniture. Re-run it after any heading change;
`--insert` refreshes the reference instead of adding a second one.

Pass `--root` whenever the document title is long: the map's root is a label, and a full
thesis title becomes a column of six short lines. `--before` decides where the reference lands;
without it, the map goes above the first module, which is also the right place.

An SVG is the only map format that survives this pipeline: Mermaid needs a CDN or a ~300 MB
`mermaid-cli`, Graphviz and PlantUML need extra binaries, and ASCII art breaks on CJK because
Chinese glyphs are double-width. SVG is vector, offline, dependency-free, and printed crisp.

**Part 2 — the body.** Modules, knowledge points and items as step 3 defined them, with no
question anywhere inside. The body ends with the corrections register from step 4, if the
lecture had errors — a table, one row per finding, in the order the pages appear.

**Part 3 — the self-test column.** The heading carries an explicit anchor:

```markdown
## 自测专栏 {#selftest}
```

The note's stylesheet turns `h2#selftest` into a page break, so the column always starts on a
fresh page. Write the anchor exactly — pandoc derives a heading's id from its text, and a
text-derived id breaks silently the moment the language changes.

Inside it, one `###` per question group, then the stem as a **blockquote** and the answer as a
**separate blockquote** right after — not one nested inside the other:

```markdown
### 自测 1｜数字修约（p7）

> **1)** Round 6.5199 to one decimal place
> **2)** Round 25.1521 to two decimal places

> 答案（p7）：1) 6.5　2) 25.15
```

Two adjacent quotes rather than one nested one, because at the back of a document the answer
must be coverable with one thumb; a nested quote cannot be covered without hiding the question.
Quote every stem, never a bare numbered list: the checker warns when items are not quoted,
because an unquoted question prints with its answer as ordinary text.

**Language.** The note follows the language the user asked in:

- **Chinese prompt → Chinese body, bilingual terms, source wording verbatim.** Every technical
  term on first use gets both languages: the Chinese term, then the English in full-width
  parentheses. The lecture's own definitions and question stems stay in the original English,
  set apart in blockquotes. Never translate a term away — the exam paper will use one of the two.
- **English prompt → English throughout**, including headings and question blocks.

Every sample and template in this skill is written in English. Render them in the user's
language, preserving the structure and the citation suffix.

Done when the file is on disk, and `scripts/check-review.py` reports no violation — map on top,
no question in the body, self-test column last.

## Step 6 — Check the note, then render it

**Check first.** The contract is mechanical, so verify it mechanically instead of by reading:

```bash
python scripts/check-review.py <out>/<name>.review.md
```

It proves three things and refuses to guess at the fourth: the map is above the first module,
no question marker appears between the first module and the self-test column, every module
comes before the self-test column, and the column's quoted items carry page citations. It
cannot prove *coverage* — that the body holds everything the lecture taught — because it cannot
see the lecture. Coverage is step 3's job and step 7's reconciliation.

Exit code 1 means a violation; fix it and re-run. Warnings (fewer than 80% of quotes cited,
unquoted items) are worth fixing too, but do not fail the run.

**Then the PDF.** Pandoc builds one self-contained HTML with native MathML, then headless
Chromium prints it. The notes reference the map by relative path, so **run pandoc from the
folder that holds the notes** — pandoc resolves a relative resource against the working
directory, not against `-o`, and from anywhere else it silently drops the map into your HTML as
a broken `src`:

```powershell
# a space-free temp folder holding the note and its map under ASCII names
$tmp = "C:\temp\review"          # no spaces, no parentheses: file:/// URLs cannot resolve them
New-Item -ItemType Directory -Force $tmp | Out-Null
Copy-Item "$out\<name>.review.md" "$tmp\notes.md"
Copy-Item "$out\<name>.review.mindmap.svg" "$tmp\notes.mindmap.svg"
# the copy now references notes.mindmap.svg; if you would rather not touch the note, pass
# --resource-path="$tmp" to pandoc and run it from anywhere

Push-Location $tmp                 # ← this is what makes the relative image resolve
pandoc "notes.md" -s --mathml --embed-resources `
  --metadata title="<title, in the user's language>" -c "<skill>\assets\review.css" `
  -o "notes.html"
Pop-Location

& "<edge-or-chrome>" --headless=new --disable-gpu --no-first-run `
  --user-data-dir="$tmp\chromeprofile" `
  --no-pdf-header-footer --print-to-pdf="$tmp\notes.pdf" "file:///$($tmp -replace '\\','/')/notes.html"
# then copy $tmp\notes.pdf back to $out\<name>.review.pdf
```

Four failure modes this avoids, all observed in practice: **a relative image path resolves
against the working directory**, so building from elsewhere silently drops the map; an
**already-running** browser absorbs the invocation so `--print-to-pdf` writes nothing (hence
`--user-data-dir`); a `file:///` URL containing spaces or parentheses does not resolve (hence
the temp folder); and a print can lose a race with profile creation and write nothing at all —
if the PDF is missing, delete the profile directory and run the browser once more before
suspecting anything else.

`--embed-resources` inlines the map as a data URI and the stylesheet into the HTML, so the PDF
is self-contained and the map stays **vector**: its text is selectable and sharp at any zoom,
which a screenshot of a diagram would not be. Confirm it took: the HTML should contain
`src="data:image/svg+xml;base64,`, not `src="<name>.mindmap.svg"`. If it still says the file
name, pandoc could not fetch the map and the PDF will show a broken-image box.

`assets/review.css` sets A4 margins, a CJK font stack, bordered compact tables, and the
`h2#selftest` page break. `--mathml` keeps formulas typeset with no network; MathJax/KaTeX would
need a CDN. Fallbacks when headless Chromium is absent, in order: LibreOffice
`--convert-to pdf`, a `pip install xhtml2pdf` HTML→PDF pass, or hand the user the Markdown and
say so — a revision note without a PDF is still the deliverable, and an honest refusal beats a
mangled render.

Then **open the PDF and look at the map page, the self-test page, a table page, and a page with
a formula.** Check: page count > 0, the map is present and legible (not blank, not a broken
image, not clipped), the self-test column starts on its own page, the user's script is not tofu
boxes, formulas are typeset rather than raw `$...$`, tables are not clipped at the margin.

Done when `check-review.py` reports no violation and that page spot check passed.

## Step 7 — Report and deliver

Present the PDF (or the Markdown, if there is no PDF), then report in the reply itself — not
only inside a file — these four things:

1. **The map** — module and knowledge-point counts, and that it was generated from the note's
   headings so it cannot drift.
2. **The self-test column** — how many question groups, how many items, how many `unanswered`,
   and every correction finding.
3. **Unreadable pages** — every `needs-vision` and `needs-human` page, with the trap and what
   was lost or rebuilt.
4. **Dropped pages** — every `drop` page with its reason code and one-line reason, so the user
   can veto any of them.

Then reconcile out loud: `total = readable + needs-vision + needs-human`, `total = keep + drop`,
and state that every `keep` page has a landing place in the body — either as items, or as
material now living in the self-test column. Any assumption you made — a merge decision, a
corrected value, a page you could not judge — belongs in this report.

Done when all four are listed, both equations balance against the input page totals, the
self-test counts match the column, and the deliverable has been presented.
