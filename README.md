# easy-college

**Agent skills that turn a lecture into study notes you can actually trust.**

Drop in a PDF, PPTX, DOCX or Markdown lecture. Get back study notes you can check: the knowledge
points, a PDF, the lecture's own questions, and an honest report of which pages the pipeline could
not read and which pages it dropped.

> **English** · [中文](README.zh-CN.md)

Built for university courseware, where the slides are ugly, the formulas are images, and the text
layer lies.

---

## Skills in this repo

A skill is a folder. Copy the folder and you have the skill. Both read the same courseware and
share the same page ledger; they differ in the document they produce.

| Skill | What it does |
|---|---|
| [`easy-learning`](skills/easy-learning/) | **Study notes for a first pass.** The lecture's prose carried over whole, with its own questions sitting next to the point they test. |
| [`easy-review`](skills/easy-review/) | **Revision notes.** A knowledge map on top, knowledge extracted completely as numbered items under modules, and every question pulled out into one self-test column at the end. |

Reach for `easy-learning` when the material is new. Reach for `easy-review` when you are revising —
or the moment you say *"put all the questions at the end"*. Three cases where it is worth saying
out loud: *"I already studied this"* → `easy-review`; *"put all the questions at the end"* →
`easy-review`; *"this is my first time with this material"* → `easy-learning`.

## Install

Three ways in. Pick the one that matches how much you intend to change.

<details open>
<summary><strong>npx — into your agent's skills directory</strong></summary>

```bash
npx github:yejianqin61-cell/easy-college        # from GitHub (works today)
npx easy-college                                # once published to npm
```

Copies both skills into `~/.agents/skills`, where agents that read that directory find them.
Re-run with `--force` to update.

```bash
npx easy-college --list          # show the skill names
npx easy-college --force         # reinstall, overwriting what is there
npx easy-college --dest <dir>    # install somewhere other than ~/.agents/skills
```

The installer only ever unlinks an existing skill that is a symlink or junction — it will not
recurse through a link and delete the directory it points at.

</details>

<details>
<summary><strong>Clone — if you want to edit the skills</strong></summary>

```bash
git clone https://github.com/yejianqin61-cell/easy-college
cp -r easy-college/skills/* ~/.agents/skills/     # or symlink them, and edit in place
```

A skill is a folder. Copy the folder and you have the skill; edit the folder and you have your own
version. Nothing here updates behind your back.

</details>

<details>
<summary><strong>Claude Code — as a plugin</strong></summary>

The repo ships a plugin and marketplace manifest, so Claude Code can install and update the whole
set as a managed bundle. In a session:

```
/plugin marketplace add yejianqin61-cell/easy-college
/plugin install easy-college@easy-college
```

The two steps are separate because `/plugin install` needs the marketplace's name (`easy-college`,
from `.claude-plugin/marketplace.json`) as a suffix. Auto-update is off by default for marketplaces
that are not Anthropic's, so turn it on from the **Marketplaces** tab in `/plugin` if you want
changes to arrive on their own.

</details>

Then just ask, in whatever words come naturally: *"turn this deck into study notes"*, or
*"I've already studied this — make revision notes, with all the questions at the end."*

## Requirements

| Need | For |
|---|---|
| Node ≥ 18 | the installer |
| Python 3 + `pymupdf` | PDF text, page renders, triage (installed on first run) |
| `pandoc` | Markdown → self-contained HTML |
| Edge or Chrome | HTML → PDF (headless) |

Missing pieces are installed by the skill on first run, and the toolchain is verified by opening a
file rather than by a successful import.

---

## The difference, in detail

The distinction is the point of this repo. Handing a student who already knows the material a note
built for someone meeting it for the first time is the failure both skills exist to prevent.

| | [`easy-learning`](skills/easy-learning/) | [`easy-review`](skills/easy-review/) |
|---|---|---|
| For | first time through the material | revising before the exam |
| Opens with | the source and its context | a **knowledge map** of the whole lecture |
| Body | the lecture's prose, carried over whole | every knowledge point as a **numbered item** under its module |
| Questions | **interleaved**, next to the point they test | **none in the body** |
| Ends with | the unreadable/dropped page report | a **self-test column**: every question, stem quoted, answer on the next line, cited by page |
| Also | — | a corrections register: every place the source contradicts itself or its own answer key |

Both read the same courseware, share the same page ledger, and obey the same rule: **every item
gets a page number**, so any line can be checked against the original.

### Documentation

One page of prose per skill, in English and in Chinese:

| Skill | English | 中文 |
|---|---|---|
| `easy-learning` | [docs/easy-learning.md](docs/easy-learning.md) | [docs/zh-CN/easy-learning.md](docs/zh-CN/easy-learning.md) |
| `easy-review` | [docs/easy-review.md](docs/easy-review.md) | [docs/zh-CN/easy-review.md](docs/zh-CN/easy-review.md) |

### Two invariants

Everything both skills do serves these two rules.

**Every page gets a verdict.** Each page of each input lands in a **ledger** with its verdict
(`readable` / `needs-vision` / `needs-human`), the trap that fired, whether it was kept or dropped, and
the reason code for the drop. The ledger reconciles at every step: *rows = the sum of all input page
counts*. An un-judged page is the failure these skills exist to prevent.

**Every item gets a page number.** No knowledge point, formula, table, question or correction enters
the notes without the source page it came from. You can open the original lecture at the cited page and
find the same content there. Notes you can check, rather than notes that sound right.

And one rule about not overstepping: **fidelity is the default.** A kept page is carried into the notes
in full — every sentence, every formula, every table, every question. The skills reorganise; they do not
decide what you do not need. Only background material (motivation, analogy, covers, dividers, breaks)
may be dropped, and every dropped page is listed for your veto.

### Language

The notes follow the language you asked in.

- **Asked in Chinese** → Chinese body, every technical term given in both languages on first use,
  and the lecture's own wording, definitions and question stems kept verbatim in English.
- **Asked in English** → English throughout.

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

The failure modes both skills are built around:

| Trap | What happens | Seen in |
|---|---|---|
| **Hidden text** | Two text spans overlap; one is painted over by a filled shape. It is invisible on the page but still extracted. | 16 pages where an invisible `34` turned a 15-element array into 19 elements — enough to generate worksheets about data that does not exist |
| **Garbled math** | An embedded math font with no `ToUnicode` map yields Arabic / Private-Use code points. `T(n) = an + b` extracts as `ܶ(݊) = ܽ݊ + ܾ`. | 13 pages |
| **Raster-only pages** | The whole page is a screenshot: a table, a formula sheet, an animation. Extractable text: 0–29 characters. | 3 pages, including one holding a lecture's entire arithmetic-operations section |
| **Full-bleed decks** | Every slide is one background bitmap, so "image coverage" carries no signal at all — a coverage threshold flags the cover and the *Thank you* slide while missing the pages that matter. | An entire 52-page deck at coverage 1.0 |
| **Duplicate frames** | Animation builds exported as consecutive slides. | 13 near-identical frames of one binary-search animation |
| **Master noise** | A footer and a logo repeated on every page. | 76 repeats of the same two tokens |
| **Errors in the source** | The lecture itself is wrong — a dropped minus sign, an answer key whose numbers do not match its questions. | 5 pages in one deck, 4 mismatched answers in another |

Each trap has a detection signature and a recovery. The catalogue is shipped inside both skills —
[`easy-learning/references/traps.md`](skills/easy-learning/references/traps.md) — and the two copies
are kept byte-identical by a test, so neither skill can drift.

---

## How it runs

`easy-learning` (a first pass):

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

`easy-review` (revision) keeps steps 0–2 and the same ledger, then replaces the back half:

| Step | Does |
|---|---|
| 3 | Promotes each knowledge point to a **numbered item** — definition, rule list, comparison table, procedure, formula block, or pitfall — under its module, dropping none of them |
| 4 | Extracts every exercise with stem, options and answer; unanswered items are the highest-value find; also builds the corrections register |
| 5 | Writes three parts: **knowledge map → itemised body → self-test column**; no question survives in the body |
| 6 | Runs `check-review.py` to verify the contract, then renders the PDF and spot-checks the map, the self-test page break, formulas and CJK |
| 7 | Reports the map and self-test counts, the unreadable pages, the dropped pages, and reconciles the counts |

Output lands in `./notes/<lecture-name>/`: the notes (`.md` and `.pdf`), the knowledge map (`.svg`),
the ledger, and page renders.

### The mind map

Every set of notes opens with one picture of the whole lecture, generated from the notes' own headings —
so it cannot drift out of sync with the document:

```bash
# first-pass notes: root → modules → knowledge points
python skills/easy-learning/scripts/mindmap.py notes/my-lecture.notes.md --insert --alt "知识结构图"

# revision notes: the same map, plus each knowledge point's `####` sub-points
python skills/easy-review/scripts/knowledge-map.py notes/my-lecture.review.md \
  --root "知识结构图" --insert --before "模块 1"
```

A right-branching map emitted as a standalone **SVG**, which is the only mind-map format that survives
an offline pipeline: Mermaid needs a CDN or a ~300 MB `mermaid-cli`, Graphviz and PlantUML need extra
binaries, and ASCII art breaks on CJK because Chinese glyphs are double-width. Being vector, it stays
sharp in print and its text stays selectable — the PDF embeds it as a data URI, so the map in the PDF
is still vector, not a screenshot.

The map is also where the heading convention pays off twice: `##` is a module, `###` a knowledge point,
and a `###`'s `####` children hang beside it. Sections that are not knowledge — the self-test column,
appendices, the errata table — are skipped, so the map shows knowledge structure rather than the
document's furniture.

### Checking a revision note

The revision contract is mechanical, so `easy-review` verifies it mechanically rather than by reading:

```bash
python skills/easy-review/scripts/check-review.py notes/my-lecture.review.md
```

It proves the map sits above the first module, that no question marker survived anywhere in the
knowledge body, that the self-test column is last, and that its quoted items carry page citations.
It cannot prove *coverage* — that the body holds everything the lecture taught — because it cannot see
the lecture; that stays the extracting agent's job, reconciled out loud at the end of the run.

---

## Layout

```
skills/
├── easy-learning/
│   ├── SKILL.md               the 8-step pipeline
│   ├── references/traps.md    the trap catalogue: signature, recovery, evidence
│   ├── scripts/triage.py      per-page triage → ledger.json / ledger.md / page renders
│   ├── scripts/mindmap.py     notes headings → a vector SVG mind map
│   └── assets/notes.css       A4, CJK-safe, compact tables
└── easy-review/
    ├── SKILL.md               the 8-step revision pipeline
    ├── references/traps.md    the same catalogue, byte-identical (a test enforces it)
    ├── scripts/triage.py      the same triage script, so this skill stands alone
    ├── scripts/knowledge-map.py   note headings → SVG, sub-points included
    ├── scripts/check-review.py    proves the revision contract holds
    └── assets/review.css      the above, plus a page break before the self-test column
docs/                          one page of prose per skill, in English and zh-CN/
bin/cli.js                     the npx installer
```

A skill folder is the unit of installation, so nothing inside one reaches into a sibling's files.

## Testing

`scripts/triage.py` was developed against two real lecture decks with deliberately different failure
modes, and re-run on both after every change — the vector-typeset deck must keep reporting 44/16/16
while the full-bleed deck reports 33/17/2. Third-party courseware is not redistributed here; the
example decks stay out of the repo, and the fixtures are generated from them at test time.

The revision pipeline is exercised the same way: a 3-module, 27-knowledge-point note over the
52-page physics deck must produce a map that fits one page with no clipped node, a
`check-review.py` run with no violation, and an 8-page A4 PDF whose map is still vector and whose
self-test column starts on its own page. `check-review.py` is then turned on eight deliberately
broken notes — map missing, map after the first module, a question left in the body, a "try the
following" prompt left in the body, no self-test column, a module after the column, an uncited
column — and must fail every one of them. A checker that only passes good input proves nothing.

A third test asserts that the two copies of `references/traps.md` are byte-identical, so the skills
cannot silently disagree about what a trap looks like.

```bash
npm test        # repo-level checks: frontmatter, self-containment, shared-file parity
```

## Contributing

One folder per skill under `skills/`, with `SKILL.md` at its root. Keep a skill self-contained: if
two skills need the same file, copy it and add it to the byte-identity check in
[`scripts/test-repo.mjs`](scripts/test-repo.mjs), the way the trap catalogue is. The conventions for
working in this repo are in [`AGENTS.md`](AGENTS.md).

## License

MIT © 2026 Ye Jianqin. See [LICENSE](LICENSE).

[中文说明 →](README.zh-CN.md)
