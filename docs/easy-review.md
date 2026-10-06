# easy-review

**Courseware in, revision notes out — a knowledge map on top, knowledge as items, and every
question in one self-test column at the end.**

`easy-review` reads the same lecture as [`easy-learning`](./easy-learning.md) and produces a
different document on purpose. A revision note is not a shorter first-pass note; it is a different
shape, built for a reader who already knows the material and needs to relocate, re-check and test
what they know.

| | |
|---|---|
| Skill file | [`skills/easy-review/SKILL.md`](../skills/easy-review/SKILL.md) |
| Invocation | model-invoked — describe the task, or say you are revising |
| Input | the same courseware `easy-learning` reads: `.pdf`, `.pptx`, `.docx`, `.html`, `.htm`, `.md`, `.txt` |
| Output | `./notes/<lecture>/`: `<name>.review.md`, `<name>.review.mindmap.svg`, `<name>.review.pdf` |
| Needs | Python 3 (HTML triage is standard library); `pymupdf` for PDFs; `pandoc`; Edge or Chrome for the PDF |

## Five rules make it a revision note

**1. It opens with the map.** The first thing after the title is one picture of the whole lecture. A
revision reader arrives knowing the material is familiar and needing to know where they are in it.

**2. Knowledge is extracted completely, as items.** The body is a complete itemised sweep: every
knowledge point of every kept page, one item per point, numbered, under the module that owns it. Each
point is *decided* — a definition, a list of rules, a comparison table, a procedure, a formula block,
a pitfall — and written as something you can check off. Rewriting prose into items is the job;
dropping a point is not.

**3. No question appears in the body.** Every exercise the lecture contains moves to the end. A
revision reader who meets a question mid-body either answers it and derails, or skips it and trains
themselves to skip. Neither is revision.

**4. The self-test column is last and is everything.** One section, at the very end, holding every
question the lecture asks, each with its stem quoted and its answer on the next line, each cited to
its page. It is the revision aid *and* the coverage proof: the questions are the lecture's own
statement of what matters.

## When it runs

Reach for it whenever the material is already familiar:

- *"I've already studied this, make revision notes."*
- *"复习资料"* / *"考前复习"* / *"二轮复习"* / *"考点整理"* / *"知识梳理"*
- *"Put all the questions at the end."* — this instruction alone selects this skill.
- *"Consolidate this lecture for the exam."*
- *"Make a knowledge map of this deck."*

## The output, part by part

```
# <lecture> — 复习笔记
> source line
![知识结构图](<name>.review.mindmap.svg)      ← 1. the map
## 模块 1｜…                                  ← 2. the body
### 1.1 …
## 复习自检｜原稿疑点与易错点                    ←    the corrections register
## 复习目标｜考前自检清单                        ← 3. the mastery checklist
## 自测专栏 {#selftest}                         ← 4. every question
```

The self-test column carries an explicit `{#selftest}` anchor because the stylesheet turns
`h2#selftest` into a page break — so the column always begins on a fresh page. Pandoc derives a
heading's id from its text, and a text-derived id would break the moment the language changed.

Inside the column, each question's stem is a blockquote and its answer is a **separate** blockquote
right after, not one nested inside the other: at the back of a document, the answer has to be
coverable with one thumb, and a nested quote cannot be covered without hiding the question.

## The knowledge map

```bash
python skills/easy-review/scripts/knowledge-map.py notes/my-lecture.review.md \
  --root "知识结构图" --insert --before "模块 1"
```

`#` is the root, `##` a module, `###` a knowledge point, and a `###`'s `####` sub-points hang beside
it — numbered rules, cases or modes, not new leaves. Sections that are not knowledge (the self-test
column, appendices, the errata table) are skipped. `--insert` refreshes the reference rather than
adding a second one, so the map can be regenerated after any heading change.

Pass `--root` when the document title is long: the map's root is a label, and a full thesis title
becomes a column of six short lines.

## The contract checker

```bash
python skills/easy-review/scripts/check-review.py notes/my-lecture.review.md
```

Exit code 0 means the document obeys its own rules:

- the map sits above the first knowledge module;
- no question marker or practice prompt survives anywhere in the knowledge body;
- the mastery checklist is present, sits before the self-test column, has a group per module, and
  cites a page on every item;
- the self-test column exists and is last — no module comes after it;
- the column is not empty, and its question groups carry page citations.

A citation may be a page (`(p42)`), an HTML unit (`(s03)`), or either form with a provenance suffix
(`(s03, rebuilt from markup)`), because the checker only has to prove that *something* citable
follows the claim.

Exit code 1 lists the violations. It is deliberately mechanical, and deliberately narrow: it cannot
prove *coverage* — that the body really holds everything the lecture taught — because it cannot see
the lecture. That stays the extracting agent's job, reconciled out loud at the end of the run.

## HTML courseware

The same lecture can arrive as `.html`, and nothing about this skill changes except what a page is.
`scripts/triage-html.py` (standard library, no install) decides the unit — a slide class, a
`<section>`, a run of siblings, or the document's own headings — records the choice as `page_model`,
and numbers the units `s01`, `s02`, … Those labels are the citations in the revision note.

It also writes `<name>.slides.md`, the deck's text layer, which keeps three channels apart: the unit
text (the only thing an item may cite), **hidden text** (`hidden`, `display:none`, `<template>` — in
the file, not on the screen, and often the answer key, so it is `needs-human` and never a silent
drop), and **speaker notes** (`<aside class="notes">` — mine it for answers, never cite it as slide
text). Hand-built formulas (`class="frac"`, `vec`) flatten in a text pass; the dump prints their
markup instead, so the formula is rebuilt exactly and cited `(s01, rebuilt from markup)`.

A saved web page is a shell whose lecture lives in the file it frames: that row is `frame-shell`, and
stdout prints the path to triage next. The ledger covers the files you actually read, and the final
report says which. The full trap-by-trap account, with the false positives already excluded
(`aria-hidden` is not hidden; an empty placeholder hides nothing), is in
[`references/traps.md`](../skills/easy-review/references/traps.md).

## Using it well

- **Say that you are revising.** A bare request for "notes" reads as a first pass. "I already
  studied this" or "复习" is the signal that selects this skill.
- **Pair it with `easy-learning` if you want both.** Studied from the first-pass notes, revise from
  these; they share the same ledger and the same citation discipline.
- **Check the corrections register first.** It collects every place the lecture contradicts itself or
  its own answer key. Revising from a wrong answer key is worse than not revising.
- **Trust the self-test column as coverage evidence.** If a question the lecture asks is missing from
  it, the extraction missed that page, and the final report will say why.

## The mastery checklist

The body says what the lecture taught. The checklist says what the reader can do — the question that
actually matters the week before an exam.

It is `## 复习目标｜考前自检清单`, holding one `- [ ]` item per knowledge point, grouped by module in
the body's order:

- **A capability, not a topic.** `能写出标准误差 $\sigma_{\bar{x}}$ 的公式并说明它与标准差
  $\sigma_x$ 差在哪里` — not `标准误差`. The heading above already names the topic.
- **Every item cites its page**, so a failed tick points at the page that fixes it.
- **The count is the coverage proof.** `check-review.py` compares it against the body's
  knowledge-point count and warns below 80%, because a checklist that is short lets a reader believe
  they are finished.
- **`- [ ]` and nothing else.** A markdown task list, so it is tickable in an editor and prints as a
  tick column.

Write it after the body, never before: a checklist written first describes the lecture the writer
expected, and revision is where that guess costs marks.

## Quoting the lecture in both languages

A Chinese note keeps the lecture's own wording in English — it is the wording the exam paper will use
— and puts the Chinese underneath it:

```markdown
> **Accuracy** is the closeness of agreement between a measured value and a true or accepted value. (p19)
>
> 译：准确度是指测量值与真值（或公认值）的接近程度。(p19)
```

The blank `>` line is what gives the translation its own paragraph; without it markdown soft-wraps the
two together and the translation reads as a continuation of the English. `check-review.py` warns about
any quoted English line in a Chinese note with no `译：` in its blockquote. An English note has none:
there is nothing to translate.
