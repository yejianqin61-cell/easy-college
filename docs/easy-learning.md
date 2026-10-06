# easy-learning

**Courseware in, study notes out — with a page verdict for every page and a page number for every
item.**

`easy-learning` produces notes for a **first pass** through a lecture: the material carried over
whole, and the lecture's own questions sitting next to the knowledge point they test, because at
that stage the question *is* part of learning the material.

If you have already studied the material and want to revise, you want
[`easy-review`](./easy-review.md) instead.

| | |
|---|---|
| Skill file | [`skills/easy-learning/SKILL.md`](../skills/easy-learning/SKILL.md) |
| Invocation | model-invoked — describe the task, or upload a lecture |
| Input | `.pdf`, `.pptx`, `.docx`, `.html`, `.htm`, `.md`, `.txt` lecture material |
| Output | `./notes/<lecture>/`: notes (`.md` + `.pdf`), a mind map (`.svg`), a ledger, page renders, and for HTML a per-unit text dump |
| Needs | Python 3 (HTML triage is standard library); `pymupdf` for PDFs; `pandoc`; Edge or Chrome for the PDF |

## When it runs

Reach for it when the lecture is new to you, or when you want the raw material preserved:

- *"Turn this deck into study notes."*
- *"整理成笔记"* / *"提炼知识点"* / *"划重点"* / *"讲义总结"*
- *"Extract the key points from these slides."*
- *"Pull the quiz questions out of this lecture."*
- *"This is my first time with this material."*

It also runs as a component: any skill that needs a lecture mined for knowledge points or self-test
items can delegate that to this one.

## What "notes you can trust" means

Two invariants do the work.

**Every page gets a verdict.** An un-judged page is the failure this skill exists to prevent, so
every page of every input lands in a **ledger**: its verdict
(`readable` / `needs-vision` / `needs-human`), the trap that fired, whether it was kept or dropped,
the reason code, and the module it fed. The ledger reconciles at every step — *rows = the sum of all
input page counts*.

**Every item gets a page number.** No knowledge point, formula, table, question or correction enters
the notes without its source page. You can open the lecture at the cited page and find that content
there. This is what makes the notes checkable instead of merely plausible.

And one rule about not overstepping: **fidelity is the default.** A kept page is carried into the
notes in full. The skill reorganises; it does not decide what you do not need. Only background
material may be dropped — motivation, analogy, covers, dividers, breaks — each with a reason code,
each listed at the end for you to veto.

## The pipeline

| Step | Does |
|---|---|
| 0 | Inventories the inputs, confirms an extractor **and** a renderer for each format, installs what is missing, and verifies by opening a file and printing its page count |
| 1 | Triages every page into the ledger and flags the trap families |
| 2 | Cuts only background, with a reason code per dropped page |
| 3 | Extracts the knowledge; formulas are rebuilt from the page render, never copied from a broken text layer |
| 4 | Collects the lecture's own questions — unanswered ones are the highest-value find |
| 5 | Writes the notes: modules, knowledge points, questions in place, citations throughout, opening with a generated mind map |
| 6 | Renders the PDF and spot-checks the map, the formulas and the CJK |
| 7 | Reports the two tails — unreadable pages, dropped pages — and reconciles the counts |

## Why it is not a text extractor

A naive extractor fails on real university decks in ways that produce confidently wrong notes. The
catalogue of those failures — with a detection signature, a recovery, and the evidence from two real
decks — is [`references/traps.md`](../skills/easy-learning/references/traps.md). The headline cases:

- **Ghost text.** Two text spans overlap, one painted over by a filled shape. Invisible on the page,
  present in the text layer. One deck hid a `34` on 16 pages, turning a 15-element array into 19 and
  generating a worksheet about data that does not exist.
- **Garbled math.** An embedded math font with no `ToUnicode` map yields Arabic and Private-Use code
  points: `T(n) = an + b` extracts as `ܶ(݊) = ܽ݊ + ܾ`.
- **Full-bleed decks.** When every slide is one background bitmap, per-page image coverage carries no
  signal at all, and a coverage threshold flags the cover slide while missing the pages that matter.
  The skill falls back to text density.
- **Author errors.** The lecture contradicts itself, or its answer key does not match its questions.
  The corrections are flagged with their page rather than silently fixed — the discrepancy is often
  the most exam-relevant thing on the page.

## HTML courseware

An HTML deck needs no package to read: `scripts/triage-html.py` is standard library, and it writes the
same ledger as the PDF path, so everything after triage is unchanged.

What differs is that an HTML file has no pages, so triage decides what one is and says so. It looks
for a slide class or `data-slide` attribute, then `<section>`s, then a run of same-tag siblings, then
top-level headings, and only then falls back to treating the whole file as one unit. The choice is
printed and recorded as `page_model`, and the units it numbers become the citation system: `(s03)`
rather than `(p42)`. When detection is wrong, `--slide-selector "section.slide"` names the element
yourself.

Alongside the ledger it writes `<name>.slides.md` — the deck's text layer, one block per unit — which
is what the extraction steps read. That dump keeps three channels apart, because in HTML they are
genuinely different things:

- the **unit text**, the only thing a knowledge point may cite;
- **hidden text** — `hidden`, `display:none`, `class="hidden"`, `<template>`. It is in the file and
  not on the screen, and in courseware it is disproportionately valuable: an answer key, a model
  answer, a control panel that appears for one geometry only, a backup slide holding the part of the
  derivation the lecturer skips. It gets `needs-human`, never a silent drop;
- **speaker notes** — `<aside class="notes">`. Mined for answers, never cited as slide text.

Three HTML signatures are worth knowing before you read a ledger:

- **Hand-built formulas.** A formula assembled from spans (`class="frac"`, `vec`, `sqrt`) flattens in
  the text layer into `E = FEqtestEq. 2.4`. The dump prints the block's markup instead, so the
  formula is rebuilt exactly, and the note cites `(s01, rebuilt from markup)`.
- **Content in a framed file.** A saved web page is a shell; its lecture lives in the sibling file it
  frames. Triage flags that row `frame-shell` and prints the path to triage next. The ledger covers
  the files you actually read, and the report says which.
- **Slides built by script.** A dev-server build (Slidev, an unbuilt Marp file) has no text in the
  file at all. That is `js-rendered`, and the answer is the built export or a browser render — not a
  guess.

Two false positives are already handled, both measured on a 700 KB lab guide: `aria-hidden="true"` is
*not* hidden (it hides content from a screen reader, not from the screen, and flagged 12 of 15 units
before the rule was narrowed), and an empty placeholder such as `<div class="feedback" hidden="">`
hides nothing.

## The mind map

Notes open with one picture of the whole lecture, generated from the notes' own headings so it cannot
drift out of sync:

```bash
python skills/easy-learning/scripts/mindmap.py notes/my-lecture.notes.md --insert --alt "知识结构图"
```

`#` is the root, `##` a module, `###` a knowledge point. A `##` section with no `###` children —
an appendix, a table of contents — is skipped, because the map shows knowledge structure rather than
the document's furniture. Output is a standalone **SVG**: vector, offline, dependency-free, sharp in
print, with selectable text.

## Using it well

- **Give it the file.** Pointing at a path beats describing the lecture.
- **Ask in your language.** Ask in Chinese and the body is Chinese with every technical term given in
  both languages, while the lecture's own wording and question stems stay in English verbatim. Ask in
  English and it is English throughout.
- **Read the final report.** It names every page that could not be read and every page dropped as
  background. A veto puts the page back into the notes as content.
- **Do not ask it to shorten.** This skill reorganises; `easy-review` is the skill that itemises. If
  you want a condensed revision document, that is a different request, not a setting.

## The mastery checklist

The notes close with `## 复习目标｜考前自检清单`: one `- [ ]` item per knowledge point, grouped by
module, each citing its page. It is the one part of the notes written for the exam rather than for the
reading — the reader ticks what they can already do and is left looking at what they cannot.

Each item states a **capability**, not a topic (`能写出标准误差 $\sigma_{\bar{x}}$ 的公式并说明它与标准差
$\sigma_x$ 差在哪里`, not `标准误差`), because the heading above already names the topic. It is written
after the body, never before.

## Quoting the lecture in both languages

A Chinese note keeps the lecture's own wording in English — the wording the exam paper will use — with
the Chinese underneath, as its own paragraph of the same blockquote:

```markdown
> **Accuracy** is the closeness of agreement between a measured value and a true or accepted value. (p19)
>
> 译：准确度是指测量值与真值（或公认值）的接近程度。(p19)
```

The blank `>` line matters: without it markdown soft-wraps the two into one paragraph and the
translation reads as a continuation of the English.
