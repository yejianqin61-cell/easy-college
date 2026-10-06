---
name: easy-review
description: "Turn courseware into revision notes: a knowledge map at the top, the lecture's knowledge points extracted completely and structured under modules as scannable items, and every exercise pulled out of the body into one self-test column at the end. Use for revision rather than first-pass learning: 复习笔记, 复习资料, 考前复习, 期末复习, 二轮复习, 知识梳理, 考点整理, 结构化笔记, 自测题汇总, 错题自测, 网页课件复习, HTML 课件, \"revision notes\", \"make revision notes from these slides\", \"consolidate this lecture for the exam\", \"put all the questions at the end\", \"I already studied this, help me revise\". The source is always the lecture: the same courseware in any format, PDF, PPTX, DOCX or HTML, read again for a different output shape. For first-time notes that interleave the lecture's questions with the material they test, use easy-learning instead. Don't use with no lecture to read, for a single-page file, or when the user only wants one question answered about a file's contents."
---

# easy-review

**A revision note is a different document from a first-pass note, not a shorter one.**

Five rules make it that document, and every step below serves them.

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

**4. It states what the reader must be able to do.** After the body comes a **mastery
checklist**: one tickable line per capability the exam will ask for, grouped by module, each
carrying its page. A revision reader needs to know not just what the lecture said but what they
personally cannot yet do, and a list they can tick is the only form that answers that. It is
derived from the body, so it is also the coverage proof in the reader's hands.

**5. The self-test column is last and is everything.** One section, at the very end, holding
every question the lecture asks, each with its stem and its answer, each cited to the page it
came from. It is both the revision aid and the coverage proof: the questions are the lecture's
own statement of what matters.

Two invariants carry over from the same source material, unchanged:

**Every page gets a verdict.** Each page of each input lands in the ledger — verdict, trap,
keep/drop, reason code, and the module it fed. The ledger reconciles at every step: **rows =
the sum of all input page counts.** In an HTML deck "page" is a decision rather than a given:
triage detects the unit (slide, `<section>`, or the whole document), records it as `page_model`,
and numbers the units `s01`, `s02`, … — which then become this deck's citation system.

**Every item gets a page number.** No knowledge point, formula, table, question or correction
enters the notes without its source page, so any line can be checked against the original. For an
HTML input that number is the ledger's unit label — `(s03)`, `(s03, rebuilt from markup)`.

Outputs land in `./notes/<input-name>/`:

| File | Holds | Read by |
|---|---|---|
| `ledger.md` / `ledger.json` | per-page verdict + trap + keep/drop + reason | the user, step 7 |
| `<name>.review.md` | the revision note: map, modules, items, self-test column | the user |
| `<name>.review.mindmap.svg` | the knowledge map, generated from the note's own headings | embedded at the top |
| `<name>.review.pdf` | the deliverable, if the renderer is available | the user |
| `pages/pNN.png` | renders, for the vision pass and for the user to check | step 1, step 7 |
| `<name>.slides.md` | HTML only: the extractable text, one block per unit, plus the hidden and speaker-note channels | steps 2–4 |

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
| `.html` / `.htm` | `scripts/triage-html.py` (standard library only) | `--render` prints the deck in headless Chromium | nothing |
| `.md` / `.txt` | read directly | none needed | — |

**Which source to read.** If this session already triaged the same lecture, reuse the renders and
the ledger — re-reading 76 pages to produce the same verdicts is waste. If it did not, triage
from scratch: `scripts/triage.py` here is the same script the `easy-learning` skill ships, and so is
`scripts/triage-html.py` for HTML, so the two agree page for page when a session uses both.

```
scripts/triage.py          per-page ledger + renders (PDF)
scripts/triage-html.py     per-unit ledger + text dump (HTML)
references/traps.md        trap signature → recovery
```

An HTML file has no page objects, so `triage-html.py` decides what a page is — a slide class, then
`<section>`s, then a run of same-tag siblings, then top-level headings, then the whole file — prints
the model it used, and records it as `page_model`. `single-document` on a deck that is visibly a
slide deck means detection failed: name the element yourself with
`--slide-selector "section.slide"`. A saved web page is a shell whose content sits in the file it
frames: the row gets `frame-shell` and stdout prints the path, so **triage that file too** and count
both ledgers as the one input. `--render` prints the deck; when the print stylesheet does not put one
slide on one page the printed page count will not match the unit count — the script says so, and a
render must then be checked against its ledger row before it is trusted.

This skill is self-contained on purpose: its folder is the unit that gets installed, and nothing
in it reaches into a sibling skill's files. If `pymupdf` cannot be installed, the two things you
lose are **the page renders** and **the trap signatures** — say so, extract with a plain
`pymupdf` text pass, and mark the ledger lower-confidence rather than pretending the traps were
checked. HTML triage needs no package at all: it is standard library, and only its optional renders
need a browser.

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
writes UTF-8, which they do. The same code page also breaks a script's *output*: printing a path like
`…\大物\week2\deck.html` into a pipe raises `UnicodeEncodeError` and kills a run that had already
finished, which is why the bundled scripts switch a redirected stdout to UTF-8 and leave a console's
own encoding alone.

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

For an HTML input, `triage-html.py` writes the same ledger plus `<name>.slides.md`, which is the
deck's text layer — one block per unit, and the thing steps 3 and 4 read. It keeps three channels
apart: the **unit text** (the only thing an item may cite), the **hidden text** (in the file, not on
the screen — often the answer key or a control panel the deck reveals later, so it is content and
gets `needs-human`), and the **speaker notes** (the presenter's private channel: mine it for answers,
never cite it). The traps and their verdicts:

| HTML trap | Verdict | Recovery |
|---|---|---|
| `hidden-content`, `hidden-slide` | `needs-human` | decide whether it belongs in the note, then carry it |
| `frame-shell` | `needs-human` | triage the framed file; this ledger does not cover it |
| `js-rendered` | `needs-vision` | render in a browser, or ask for the built deck |
| `image-only`, `math-image`, `svg-only` | `needs-vision` | read the render, cite `(s12, rebuilt from image)` |
| `thin-text`, `empty-text` | `needs-vision` | a picture-led deck: read the render |
| `image-alt` | `readable` | the picture's content is in its `alt`; cite `(s12, from alt text)` |
| `formula-markup` | `readable` | rebuild from the markup block in the dump, never from the flattened line |
| `math-source` | `readable` | the LaTeX sits in the markup; use it verbatim |
| `fragments`, `speaker-notes`, `duplicate` | `readable` | a click-to-reveal build, a private channel, or a repeat — decide by step 2, never by reflex |

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
  from a render rather than the text layer. For an HTML source it is the ledger's unit label:
  `(s03)`, `(s03, from alt text)`, `(s03, rebuilt from markup)`.
- Formulas are inline LaTeX: `$T^{2} = 4\pi^{2}L/g$`. **No space inside a `$...$` span** — `$E = $ 5850`
  is not math to pandoc and prints its dollars literally, so the note ships the formula as source.
  A space *before* an opening `$` is fine; display math (`$$...$$`) is untouched.
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
## 复习目标｜考前自检清单          ← part 3: the mastery checklist
## 自测专栏 {#selftest}          ← part 4: every question
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

**Part 3 — the mastery checklist.** `## 复习目标｜考前自检清单`. The heading carries a
document-furniture word on purpose: the map script and the checker both skip this section, so the
map keeps showing knowledge structure rather than a second copy of the body.

Open the section with one line telling the reader how to use it, then one `###` per module in the
body's order, then one tickable item per knowledge point:

```markdown
## 复习目标｜考前自检清单

> 逐条自问：合上笔记，能否说出或写出这一条？能就打勾。

### 1｜如何正确表达一个数

- [ ] 能说清修约的三条规则，并用「向偶数靠」处理 $3.55$ 与 $3.65$ 这类恰好为 5 的情形（p6）
- [ ] 能判断一个数有几位有效数字，包括末尾零与前导零两类陷阱（p9–p10）
- [ ] 能把任意数写成 $m \times 10^{n}$ 且 $1 \le m < 10$（p12）
```

Four rules make it a checklist rather than a table of contents:

- **A capability, not a topic.** `能写出标准误差 $\sigma_{\bar{x}}$ 的公式并说明它与标准差
  $\sigma_x$ 差在哪里` — not `标准误差`. The heading already names the topic; the checklist says
  what the reader must be able to *do* with it.
- **One item per knowledge point, at least.** The count is the coverage proof: fewer items than
  the body has knowledge points means something was dropped, and `check-review.py` warns on exactly
  that comparison. Group the items under their module, in the body's order.
- **A page citation on every item** — the same invariant as everything else, and what makes a
  failed tick traceable to the page that fixes it.
- **`- [ ]` and nothing else.** A markdown task list, so the reader can tick it in an editor and
  the PDF prints a checkbox column.

Write the items after the body is finished, never before: a checklist written first describes the
lecture the writer expected, and revision is where that guess costs the reader marks.

**Part 4 — the self-test column.** The heading carries an explicit anchor:

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

- **Chinese prompt → Chinese body, bilingual terms, every quoted original translated.** Write the
  body in Chinese, and on first use give every technical term in both languages: the Chinese term,
  then the English in full-width parentheses. The lecture's own definitions and question stems stay
  in the original English, set apart in blockquotes — **and each English quote is followed by its
  Chinese translation**, as its own paragraph of the same blockquote (a blank `>` line, then the
  translation), introduced by `译：`:

  ```markdown
  > **Accuracy** is the closeness of agreement between a measured value and a true or accepted
  > value. (p19)
  >
  > 译：准确度是指测量值与真值（或公认值）的接近程度。(p19)

  > **1)** Round 6.5199 to one decimal place
  > **2)** Round 25.1521 to two decimal places
  >
  > 译：1) 将 6.5199 修约到一位小数　2) 将 25.1521 修约到两位小数
  ```

  The blank `>` matters: without it markdown soft-wraps the two into one paragraph and the
  translation reads as a continuation of the English. Both halves earn their place: the
  translation is what the reader revises from, and the original is what the exam paper will use.
  Never translate a term away, and never replace the English with the Chinese — a quote is the
  lecture's wording or it is not a quote.
- **English prompt → English throughout**, including headings and question blocks. No `译：` lines:
  there is nothing to translate.

Every sample and template in this skill is written in English. Render them in the user's
language, preserving the structure and the citation suffix.

Done when the file is on disk, and `scripts/check-review.py` reports no violation — map on top,
no question in the body, checklist covering every module, self-test column last — and, in a Chinese
note, no quoted English original is left untranslated.

## Step 6 — Check the note, then render it

**Check first.** The contract is mechanical, so verify it mechanically instead of by reading:

```bash
python scripts/check-review.py <out>/<name>.review.md
```

It proves four things and refuses to guess at the fifth: the map is above the first module, no
question marker appears between the first module and the self-test column, the mastery checklist
sits before the self-test column with a group per module and a page on every item, and the column's
quoted items carry page citations. It cannot prove *coverage* — that the body holds everything the
lecture taught — because it cannot see the lecture. Coverage is step 3's job and step 7's
reconciliation.

Exit code 1 means a violation; fix it and re-run. Warnings are worth fixing too but do not fail
the run: fewer than 80% of quoted items cited, unquoted items, a checklist with fewer items than
the body has knowledge points, and quoted English lines with no `译：` translation in a Chinese
note.

**Then the PDF.** Pandoc builds one self-contained HTML with native MathML, then headless
Chromium prints it. The notes reference the map by relative path, so **run pandoc from the
folder that holds the notes** — pandoc resolves a relative resource against the working
directory, not against `-o`, and from anywhere else it silently drops the map into your HTML as
a broken `src`:

```powershell
# a space-free temp folder holding the note and its map under their OWN names
$tmp = "C:\temp\review"          # no spaces, no parentheses: file:/// URLs cannot resolve them
New-Item -ItemType Directory -Force $tmp | Out-Null
Copy-Item "$out\<name>.review.md" "$tmp\"
Copy-Item "$out\<name>.review.mindmap.svg" "$tmp\"
# keep the names: the note references its map by file name, so renaming the copy — to `notes.md`
# and `notes.mindmap.svg`, say — leaves the reference pointing at nothing and pandoc embeds no map

Push-Location $tmp                 # ← this is what makes the relative image resolve
pandoc "<name>.review.md" -s --mathml --embed-resources `
  --metadata title="<title, in the user's language>" -c "<skill>\assets\review.css" `
  -o "notes.html"
Pop-Location

& "<edge-or-chrome>" --headless=new --disable-gpu --no-first-run `
  --user-data-dir="$tmp\chromeprofile" `
  --no-pdf-header-footer --print-to-pdf="$tmp\notes.pdf" "file:///$($tmp -replace '\\','/')/notes.html"
# then copy $tmp\notes.pdf back to $out\<name>.review.pdf
```

Four failure modes this avoids, all observed in practice: **a relative image path resolves
against the working directory**, so building from elsewhere silently drops the map; renaming the
copied map while the note still references the old name drops it just as silently; an
**already-running** browser absorbs the invocation so `--print-to-pdf` writes nothing (hence
`--user-data-dir`); and a `file:///` URL containing spaces or parentheses does not resolve (hence
the temp folder).

**Print in a retry loop, not once, and wait for the file rather than sleeping a fixed time.** On a
14-page note, three of four attempts failed that way, and a single check three seconds after the
launcher returns reports failure on a print that is merely slow — poll, and require a non-empty file:

```powershell
for ($i = 1; $i -le 4; $i++) {
  Remove-Item "$tmp\notes.pdf" -ErrorAction SilentlyContinue
  & "<edge-or-chrome>" --headless=new --disable-gpu --no-first-run `
    --user-data-dir="$tmp\p$i" --no-pdf-header-footer `
    --print-to-pdf="$tmp\notes.pdf" "file:///<tmp>/notes.html" 2>$null
  for ($t = 0; $t -lt 30; $t++) {                 # the print is slow, not absent
    if ((Test-Path "$tmp\notes.pdf") -and (Get-Item "$tmp\notes.pdf").Length -gt 0) { break }
    Start-Sleep -Seconds 1
  }
  if ((Test-Path "$tmp\notes.pdf") -and (Get-Item "$tmp\notes.pdf").Length -gt 0) { break }
}
```

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
only inside a file — these five things:

1. **The map** — module and knowledge-point counts, and that it was generated from the note's
   headings so it cannot drift.
2. **The mastery checklist** — how many modules it covers and how many tickable items it holds,
   against the body's knowledge-point count.
3. **The self-test column** — how many question groups, how many items, how many `unanswered`,
   and every correction finding.
4. **Unreadable pages** — every `needs-vision` and `needs-human` page, with the trap and what
   was lost or rebuilt.
5. **Dropped pages** — every `drop` page with its reason code and one-line reason, so the user
   can veto any of them.

Then reconcile out loud: `total = readable + needs-vision + needs-human`, `total = keep + drop`,
and state that every `keep` page has a landing place in the body — either as items, or as
material now living in the self-test column. For an HTML source, also state the `page_model` the
ledger used, the unit count, and any file it frames that you triaged as well. Any assumption you
made — a merge decision, a corrected value, a page you could not judge — belongs in this report.

Done when all five are listed, both equations balance against the input page totals, the
self-test counts match the column, and the deliverable has been presented.
