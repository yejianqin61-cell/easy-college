# easy-college

**Agent skills that turn a lecture into study notes you can actually trust.**

Drop in a PDF, PPTX, DOCX or Markdown lecture. Get back a structured Markdown of the knowledge
points, a PDF, the lecture's own self-test questions in place next to the material they test — and an
honest report of which pages the pipeline could not read and which pages it dropped.

Built for university courseware, where the slides are ugly, the formulas are images, and the text layer
lies.

```
npx github:yejianqin61-cell/easy-college
```

> Also available as `npx easy-college` once the package is published to npm.

---

## Why this exists

Extracting notes from a lecture deck looks like a text-extraction problem. It is not. It is a
**trust** problem: the text layer is full of content that is not on the page, and the page is full of
content that is not in the text layer.

Both of these decks are real, and both broke naive extraction in different ways:

| Deck | Pages | Result |
|---|---|---|
| A 76-page CS lecture (data structures) | 76 | 44 readable · 16 needs-vision · 16 needs-human |
| A 52-page physics lab lecture (error analysis) | 52 | 33 readable · 17 needs-vision · 2 needs-human |

The failure modes `easy-learning` is built around:

| Trap | What happens | Seen in |
|---|---|---|
| **Hidden text** | Two text spans overlap; one is painted over by a filled shape. It is invisible on the page but still extracted. | 16 pages where an invisible `34` turned a 15-element array into 19 elements — enough to generate worksheets about data that does not exist |
| **Garbled math** | An embedded math font with no `ToUnicode` map yields Arabic / Private-Use code points. `T(n) = an + b` extracts as `ܶ(݊) = ܽ݊ + ܾ`. | 13 pages |
| **Raster-only pages** | The whole page is a screenshot: a table, a formula sheet, an animation. Extractable text: 0–29 characters. | 3 pages, including one holding a lecture's entire arithmetic-operations section |
| **Full-bleed decks** | Every slide is one background bitmap, so "image coverage" carries no signal at all — a coverage threshold flags the cover and the *Thank you* slide while missing the pages that matter. | An entire 52-page deck at coverage 1.0 |
| **Duplicate frames** | Animation builds exported as consecutive slides. | 13 near-identical frames of one binary-search animation |
| **Master noise** | A footer and a logo repeated on every page. | 76 repeats of the same two tokens |
| **Errors in the source** | The lecture itself is wrong — a dropped minus sign, an answer key whose numbers do not match its questions. | 5 pages in one deck, 4 mismatched answers in another |

Each trap has a detection signature and a recovery, documented in
[`skills/easy-learning/references/traps.md`](skills/easy-learning/references/traps.md).

---

## Two invariants

Everything the skill does serves these two rules.

**Every page gets a verdict.** Each page of each input lands in a **ledger** with its verdict
(`readable` / `needs-vision` / `needs-human`), the trap that fired, whether it was kept or dropped, and
the reason code for the drop. The ledger reconciles at every step: *rows = the sum of all input page
counts*. An un-judged page is the failure this skill exists to prevent.

**Every item gets a page number.** No knowledge point, formula, table, question or correction enters
the notes without the source page it came from. You can open the original lecture at the cited page and
find the same content there. Notes you can check, rather than notes that merely sound right.

And one rule about not overstepping: **fidelity is the default.** A kept page is carried into the notes
in full — every sentence, every formula, every table, every question. The skill reorganises; it does not
decide what you do not need. Only background material (motivation, analogy, covers, dividers, breaks)
may be dropped, and every dropped page is listed for your veto.

## Language

The notes follow the language you asked in.

- **Asked in Chinese** → Chinese body, every technical term given in both languages on first use,
  and the lecture's own wording, definitions and question stems kept verbatim in English.
- **Asked in English** → English throughout.

---

## How it runs

| Step | Does |
|---|---|
| 0 | Inventories the inputs, confirms an extractor and a renderer for each, installs anything missing, and verifies by actually opening a file |
| 1 | Triages **every page** and builds the ledger |
| 2 | Drops only the background, with a reason code per page |
| 3 | Extracts knowledge, formulas and derivations — formulas rebuilt from the render, never copied from a broken text layer |
| 4 | Collects the lecture's own questions; unanswered ones are the highest-value find |
| 5 | Writes the Markdown: modules, knowledge points, questions in place, page citations throughout — opening with a mind map generated from the notes' own headings |
| 6 | Renders the PDF (pandoc → native MathML → headless Chromium) and checks that the map, formulas and CJK actually rendered |
| 7 | Reports the two tails — unreadable pages, dropped pages — and reconciles the counts |

Output lands in `./notes/<lecture-name>/`: the notes (`.md` and `.pdf`), the overview map (`.svg`), the
ledger, and page renders.

### The mind map

Every set of notes opens with one picture of the whole lecture, generated from the notes' own headings —
so it cannot drift out of sync with the document:

```bash
python skills/easy-learning/scripts/mindmap.py notes/my-lecture.notes.md --insert --alt "知识结构图"
```

A right-branching map (root → modules → knowledge points) emitted as a standalone **SVG**, which is the
only mind-map format that survives an offline pipeline: Mermaid needs a CDN or a ~300 MB
`mermaid-cli`, Graphviz and PlantUML need extra binaries, and ASCII art breaks on CJK because Chinese
glyphs are double-width. Being vector, it stays sharp in print and its text stays selectable.

---

## Install

```bash
# from GitHub (works today)
npx github:yejianqin61-cell/easy-college

# from npm, once published
npx easy-college
```

Options:

```bash
npx easy-college --list          # show the skill names
npx easy-college --force         # reinstall, overwriting what is there
npx easy-college --dest <dir>    # install somewhere other than ~/.agents/skills
```

The installer only ever unlinks an existing skill that is a symlink or junction — it will not recurse
through a link and delete the directory it points at.

## Requirements

| Need | For |
|---|---|
| Node ≥ 18 | the installer |
| Python + `pymupdf` | PDF text, rendering and triage (installed on first run) |
| `pandoc` | Markdown → self-contained HTML |
| Edge or Chrome | HTML → PDF (headless) |

Missing pieces are installed by the skill on first run, and the toolchain is verified by opening a file
rather than by a successful import.

---

## Skills in this repo

| Skill | Does |
|---|---|
| [`easy-learning`](skills/easy-learning/) | Courseware → notes. The full pipeline above. |

<!-- More skills land here. -->

## Layout

```
skills/easy-learning/
├── SKILL.md               the 8-step pipeline
├── references/traps.md    the trap catalogue: signature, recovery, evidence
├── scripts/triage.py      per-page triage → ledger.json / ledger.md / page renders
├── scripts/mindmap.py     notes headings → a vector SVG mind map
└── assets/notes.css       A4, CJK-safe, compact tables
bin/cli.js                 the npx installer
```

## Testing

`scripts/triage.py` was developed against two real lecture decks with deliberately different failure
modes, and re-run on both after every change — the vector-typeset deck must keep reporting 44/16/16
while the full-bleed deck reports 33/17/2. Third-party courseware is not redistributed here.

## License

MIT © 2026 Ye Jianqin. See [LICENSE](LICENSE).

[中文说明 →](README.zh-CN.md)
