#!/usr/bin/env node
/**
 * Repo-level tests for easy-college.
 *
 * These check the things that rot silently: a skill that reaches into a sibling skill's files, two
 * copies of a shared catalogue drifting apart, a description that stopped describing when to invoke
 * the skill, a plugin manifest listing a skill that no longer exists.
 *
 * The per-skill *pipelines* are not tested here — they are run end to end against a real lecture
 * deck, as the Testing section of the README describes. This file guards the repository's shape.
 *
 * Usage: node scripts/test-repo.mjs   (or: npm test)
 * Exit:  0 all checks pass | 1 at least one check failed
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKILLS = path.join(REPO, 'skills');

let failures = 0;
const pass = (msg) => console.log(`  ok    ${msg}`);
const fail = (msg) => {
  console.log(`  FAIL  ${msg}`);
  failures += 1;
};
const section = (title) => console.log(`\n== ${title} ==`);

const skillNames = fs
  .readdirSync(SKILLS, { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name)
  .sort();

/** Keys the skill loader never reads, so they belong in the README instead. */
const IGNORED_KEYS = ['license', 'compatibility', 'metadata', 'version'];

function readFrontmatter(file) {
  const text = fs.readFileSync(file, 'utf8');
  if (!text.startsWith('---\n')) return null;
  const end = text.indexOf('\n---', 3);
  if (end === -1) return null;
  const block = text.slice(4, end);
  const out = {};
  for (const line of block.split('\n')) {
    const m = /^([A-Za-z_-]+):\s*(.*)$/.exec(line);
    if (m) out[m[1]] = m[2];
  }
  return { keys: Object.keys(out), ...out };
}

section('every skill has a SKILL.md with conforming frontmatter');
for (const name of skillNames) {
  const skill = path.join(SKILLS, name, 'SKILL.md');
  if (!fs.existsSync(skill)) {
    fail(`${name}: no SKILL.md`);
    continue;
  }
  const fm = readFrontmatter(skill);
  if (!fm) {
    fail(`${name}: frontmatter does not open the file`);
    continue;
  }
  if (fm.name !== name) fail(`${name}: frontmatter name is '${fm.name}', must equal the folder name`);
  const description = (fm.description ?? '').replace(/^"|"$/g, '');
  if (!description) fail(`${name}: no description in frontmatter`);
  else if (description.length < 200) {
    fail(`${name}: description is ${description.length} chars; it must say when the skill applies`);
  }
  const extra = fm.keys.filter((k) => IGNORED_KEYS.includes(k));
  if (extra.length) fail(`${name}: frontmatter carries keys the loader ignores: ${extra.join(', ')}`);
  if (!extra.length && fm.name === name && description.length >= 200) {
    pass(`${name}: frontmatter conforms (${description.length}-char description)`);
  }
}

section('a skill folder stands alone');
// Nothing inside skills/<a>/ may reference a file inside skills/<b>/. A user can install either one
// on its own, so a cross-skill path is a broken link nobody notices until a run fails.
const CROSS = /\beasy-(learning|review)\/(scripts|assets|references)\//;
for (const name of skillNames) {
  const root = path.join(SKILLS, name);
  const offenders = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (!/\.(md|py|css|json)$/.test(entry.name)) continue;
      else {
        const text = fs.readFileSync(full, 'utf8');
        text.split('\n').forEach((line, i) => {
          // The failure is a path into a sibling skill's tree. Prose that names a sibling skill
          // ("use easy-review instead") is documentation, not a link.
          if (CROSS.test(line)) {
            offenders.push(`${path.relative(REPO, full)}:${i + 1}: ${line.trim()}`);
          }
        });
      }
    }
  };
  walk(root);
  if (offenders.length) {
    fail(`${name}: references a sibling skill's files`);
    offenders.forEach((o) => console.log(`          ${o}`));
  } else {
    pass(`${name}: no cross-skill file paths`);
  }
}

section('shared files are byte-identical');
const SHARED = [
  ['references/traps.md', 'references/traps.md'],
  ['scripts/triage.py', 'scripts/triage.py'],
  ['scripts/triage-html.py', 'scripts/triage-html.py'],
];
for (const [a, b] of SHARED) {
  const first = path.join(SKILLS, 'easy-learning', a);
  const second = path.join(SKILLS, 'easy-review', b);
  if (!fs.existsSync(first)) fail(`${a}: missing`);
  else if (!fs.existsSync(second)) fail(`${b}: missing`);
  else if (fs.readFileSync(first).equals(fs.readFileSync(second))) {
    pass(`${a}: both copies identical (${fs.statSync(first).size} bytes)`);
  } else {
    fail(`${a}: the two copies differ`);
  }
}

section('the HTML triage answers every unit and flags the HTML traps');
// The fixture is generated here rather than committed: third-party decks are not redistributable,
// and a four-slide file with one trap per slide is a better test than a real deck anyway -- it says
// exactly which signature must fire. The script itself is standard library, so Python is the only
// requirement; without it the check is skipped, not failed.
function findPython() {
  for (const candidate of [process.env.PYTHON, 'python3', 'python']) {
    if (!candidate) continue;
    try {
      execFileSync(candidate, ['-c', 'print(1)'], { stdio: 'ignore' });
      return candidate;
    } catch {
      /* try the next interpreter */
    }
  }
  return null;
}

const python = findPython();
if (!python) {
  pass('skipped: no python interpreter found (set PYTHON to run it)');
} else {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'easy-college-html-'));
  const deck = path.join(tmp, 'deck.html');
  fs.writeFileSync(
    path.join(tmp, 'frame.html'),
    `<!DOCTYPE html><html><body>${'<p>The framed lab sheet carries the whole procedure, the data table and the questions, so a reader who has only this file can still do the work.</p>'.repeat(6)}</body></html>`,
  );
  fs.writeFileSync(
    deck,
    `<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>fixture</title>
<style>.answer{display:none}</style></head>
<body><div class="slides">
<section class="slide"><h2>Hidden material</h2><p>Visible prose here.</p>
  <div class="field" hidden=""><label>Arc angle, 2&#966;</label></div>
  <div class="feedback" hidden=""></div></section>
<section class="slide"><h2>Diagram</h2><p>Map.</p><img src="map.png"></section>
<section class="slide"><h2>Formula</h2><p>From Gauss's law.</p>
  <div class="eq" aria-label="E vector equals F vector divided by q test">
    <i class="vec">E</i> = <span class="frac"><span><i>F</i></span><span><i>q</i></span></span>
  </div></section>
<section class="slide"><h2>Framed sheet</h2><iframe src="frame.html"></iframe></section>
</div><script>/* deck script */</script></body></html>`,
  );

  const out = path.join(tmp, 'notes');
  try {
    execFileSync(python, [path.join(SKILLS, 'easy-learning', 'scripts', 'triage-html.py'), deck, '--out', out], {
      encoding: 'utf8',
    });
    const ledger = JSON.parse(fs.readFileSync(path.join(out, 'deck', 'ledger.json'), 'utf8'));
    const rows = ledger.pages;
    const expected = [
      ['hidden-content', 'needs-human'],
      ['image-only', 'needs-vision'],
      ['formula-markup', 'readable'],
      ['frame-shell', 'needs-human'],
    ];
    if (ledger.page_model !== 'marked-slides') {
      fail(`page model is '${ledger.page_model}', expected marked-slides`);
    } else if (rows.length !== 4) {
      fail(`triaged ${rows.length} unit(s), expected 4`);
    } else {
      pass(`4 slides via marked-slides, labels ${rows.map((r) => r.label).join(' ')}`);
    }
    for (const [trap, verdict] of expected) {
      const hit = rows.find((r) => r.traps.includes(trap));
      if (!hit) fail(`no row reported the ${trap} trap`);
      else if (hit.verdict !== verdict) {
        fail(`${trap} produced verdict '${hit.verdict}', expected '${verdict}'`);
      } else {
        pass(`${trap} -> ${verdict} on ${hit.label}`);
      }
    }
    // The invariant the whole skill rests on: every unit has exactly one verdict, and they add up.
    const counted = rows.reduce((n, r) => n + (['readable', 'needs-vision', 'needs-human'].includes(r.verdict) ? 1 : 0), 0);
    if (counted !== rows.length) fail(`${rows.length - counted} unit(s) have no verdict`);
    else pass(`every one of ${rows.length} unit(s) carries exactly one verdict`);
    // And the text dump is the thing the extraction steps actually read.
    const dump = fs.readFileSync(path.join(out, 'deck', 'deck.slides.md'), 'utf8');
    const missing = ['### s01', '### s04', 'Formula markup', 'Hidden text', 'frame.html'].filter(
      (marker) => !dump.includes(marker),
    );
    if (missing.length) fail(`the dump is missing: ${missing.join(', ')}`);
    else pass('the dump carries every unit, plus the markup, hidden and framed channels');
  } catch (error) {
    fail(`triage-html.py failed: ${error.message}`);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

section('the plugin lists every skill, and only skills that exist');
const plugin = path.join(REPO, '.claude-plugin', 'plugin.json');
if (!fs.existsSync(plugin)) fail('no .claude-plugin/plugin.json');
else {
  const manifest = JSON.parse(fs.readFileSync(plugin, 'utf8'));
  const listed = (manifest.skills ?? []).map((s) => s.replace(/^\.\//, '').replace(/\/$/, ''));
  for (const name of skillNames) {
    if (!listed.includes(`skills/${name}`)) fail(`plugin.json does not list ./skills/${name}`);
  }
  for (const entry of listed) {
    if (!fs.existsSync(path.join(REPO, entry, 'SKILL.md'))) {
      fail(`plugin.json lists ${entry}, which is not a skill`);
    }
  }
  if (JSON.stringify(listed.slice().sort()) === JSON.stringify(skillNames.map((n) => `skills/${n}`))) {
    pass(`plugin.json lists exactly: ${skillNames.join(', ')}`);
  }
}

section('the installer finds every skill');
try {
  const out = execFileSync(process.execPath, [path.join(REPO, 'bin', 'cli.js'), '--list'], {
    encoding: 'utf8',
  })
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
    .sort();
  if (out.join(' ') === skillNames.join(' ')) pass(`cli.js --list reports: ${out.join(', ')}`);
  else fail(`cli.js --list reports '${out.join(', ')}', disk has '${skillNames.join(', ')}'`);
} catch (error) {
  fail(`cli.js --list failed: ${error.message}`);
}

section('documentation exists for every skill');
for (const name of skillNames) {
  if (fs.existsSync(path.join(REPO, 'docs', `${name}.md`))) pass(`docs/${name}.md`);
  else fail(`docs/${name}.md is missing`);
  if (fs.existsSync(path.join(REPO, 'docs', 'zh-CN', `${name}.md`))) {
    pass(`docs/zh-CN/${name}.md`);
  } else {
    fail(`docs/zh-CN/${name}.md is missing (both READMEs link it)`);
  }
}
for (const readme of ['README.md', 'README.zh-CN.md']) {
  const text = fs.readFileSync(path.join(REPO, readme), 'utf8');
  const missing = skillNames.filter((n) => !text.includes(n));
  if (missing.length) fail(`${readme} does not mention: ${missing.join(', ')}`);
  else pass(`${readme} mentions every skill`);
}

section('the two READMEs link to each other and lead with the skills');
for (const [readme, other] of [['README.md', 'README.zh-CN.md'], ['README.zh-CN.md', 'README.md']]) {
  const text = fs.readFileSync(path.join(REPO, readme), 'utf8');
  const lines = text.split('\n');
  const linkAt = lines.findIndex((l) => l.includes(`](${other})`));
  if (linkAt === -1) {
    fail(`${readme} does not link to ${other}`);
    continue;
  }
  // "Up front" is a measurable claim: the switch sits in the header block, and the skills table
  // arrives before the install steps.
  const skillsAt = lines.findIndex((l) => /^##\s+(Skills in this repo|本仓库的技能)/.test(l));
  const installAt = lines.findIndex((l) => /^##\s+(Install|安装)/.test(l));
  if (linkAt > 12) fail(`${readme}: the ${other} link is at line ${linkAt + 1}, not in the header`);
  if (skillsAt === -1) fail(`${readme}: no skills section`);
  else if (installAt === -1) fail(`${readme}: no install section`);
  else if (skillsAt > installAt) fail(`${readme}: install comes before the skills list`);
  else pass(`${readme}: language link at line ${linkAt + 1}, skills at ${skillsAt + 1}, install at ${installAt + 1}`);
}

section('every relative link resolves');
// A README that links a file that does not exist is worse than one that links nothing, and the
// docs table makes that easy to get wrong in one language only. Only git-tracked .md files are
// checked: scratch under work/ is generated, and a test fixture's placeholder links are its point.
const LINK = /\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
const SKIP_DIRS = new Set(['.git', 'node_modules', 'work', 'notes', 'example']);
let links = 0;
const broken = [];
const walkAll = (dir) => {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name)) continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkAll(full);
    } else if (entry.name.endsWith('.md')) {
      const text = fs.readFileSync(full, 'utf8');
      for (const match of text.matchAll(LINK)) {
        const target = match[1];
        if (/^(https?:|mailto:|#)/.test(target)) continue;
        // `<name>.review.pdf` and friends are path *patterns* in documentation, not links.
        if (/[<>{}]/.test(target)) continue;
        links += 1;
        const clean = target.split('#')[0];
        if (!clean) continue;
        if (!fs.existsSync(path.resolve(path.dirname(full), decodeURIComponent(clean)))) {
          broken.push(`${path.relative(REPO, full)} -> ${target}`);
        }
      }
    }
  }
};
walkAll(REPO);
if (broken.length) {
  fail(`${broken.length} broken relative link(s):`);
  broken.forEach((b) => console.log(`          ${b}`));
} else {
  pass(`all ${links} relative link(s) resolve`);
}

console.log('');
if (failures === 0) {
  console.log('PASS  all repo-level checks passed');
  process.exit(0);
}
console.log(`FAIL  ${failures} check(s) failed`);
process.exit(1);
