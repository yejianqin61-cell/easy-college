# Working in this repo

Conventions for an agent editing **easy-college** itself. If you are here to *use* the skills
rather than change them, read the [README](./README.md) instead.

## What this repo is

A collection of agent skills. A skill is a folder under `skills/` whose root holds a `SKILL.md` with
YAML frontmatter. The folder is the unit of installation: `bin/cli.js` copies each one into the
user's skills directory, and the Claude Code plugin lists each one by path. Nothing else in the repo
is installed.

```
skills/<skill-name>/SKILL.md      the skill
skills/<skill-name>/references/   catalogues and reference material the skill reads
skills/<skill-name>/scripts/      runnable steps
skills/<skill-name>/assets/       stylesheets and other build inputs
docs/<skill-name>.md              prose documentation, one page per skill
docs/zh-CN/<skill-name>.md        the same page in Chinese — both READMEs link both
bin/cli.js                        the installer
scripts/test-repo.mjs             repo-level tests (`npm test`)
```

**The repo root is also the plugin root.** `.claude-plugin/plugin.json` and `marketplace.json`
declare the two skills by path, so installing the plugin installs exactly the same folders the
installer copies. Verify a manifest change with `claude plugin validate .`, which reports
`Validation passed with warnings` today: the warning is that `CLAUDE.md` at the plugin root is not
loaded as project context. That is expected — it is the contributor pointer, not plugin content —
so do not silence it by deleting the file.

## Rules

**A skill folder must stand alone.** Nothing inside `skills/<a>/` may reference a file inside
`skills/<b>/`. When two skills genuinely need the same file, copy it and register the copy in
`scripts/test-repo.mjs`, which asserts the copies stay byte-identical. `references/traps.md`,
`scripts/triage.py` and `scripts/triage-html.py` are shared between `easy-learning` and `easy-review`
this way. The reason is concrete: a user can install either skill on its own, and a cross-skill path
turns into a broken link that nobody notices until a run fails.

**Frontmatter carries only what the loader reads.**

```yaml
---
name: <skill-name>          # must equal the folder name
description: "<one line>"    # the only thing an agent sees when deciding to invoke the skill
---
```

No `version`, `license`, `metadata` or `compatibility` keys. The licence is in `LICENSE`, the
requirements are in the README, and a version per skill would need bumping in four places.

The description is load-bearing. It states *when* the skill applies, in the words a user would
actually type — including the Chinese phrasings — and ends with what it does **not** cover and which
sibling to use instead. Two skills that read the same input must be separable from their
descriptions alone.

**Both READMEs are first-class.** `README.md` and `README.zh-CN.md` mirror each other section for
section, and each links the other in its header block. Both lead with the skills table, then install,
then the detail — a reader should learn what the repo contains and how to get it before any
explanation of why. `npm test` asserts the ordering and the mutual link, so it cannot rot silently.

**Documentation is bilingual.** Every `docs/<skill>.md` has a `docs/zh-CN/<skill>.md`. Keep the two in
step section for section; a translation that lags is worse than none, because it is trusted. Relative
links from `docs/zh-CN/` need one more `../` than from `docs/`, which `npm test` also checks.

**Every skill flow states a "Done when" per step.** A step without an observable completion
condition is a step an agent will skip.

**Test the tooling, not just the prose.** Anything with a script is expected to be run end to end
against a real deck before it is called done. See `scripts/test-repo.mjs`.

## Before you commit

```bash
npm test                           # repo-level tests: frontmatter, self-containment, shared-file parity
node bin/cli.js --list             # the installer still discovers every skill
```

Anything under `work/`, `notes/` or `example/` is scratch or third-party courseware and is
gitignored — never force-add it. Third-party decks are not redistributable, so tests generate their
fixtures from a deck at run time rather than committing them.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with the frontmatter above.
2. Write it as a pipeline with numbered steps and a "Done when" per step.
3. Add the skill path to `["skills"]` in `.claude-plugin/plugin.json`.
4. Add it to the skills table near the top of both READMEs, and to their docs tables.
5. Add `docs/<name>.md` and `docs/zh-CN/<name>.md`, following the shape of the existing pages.
6. Run `npm test`.
