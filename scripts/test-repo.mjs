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
}
for (const readme of ['README.md', 'README.zh-CN.md']) {
  const text = fs.readFileSync(path.join(REPO, readme), 'utf8');
  const missing = skillNames.filter((n) => !text.includes(n));
  if (missing.length) fail(`${readme} does not mention: ${missing.join(', ')}`);
  else pass(`${readme} mentions every skill`);
}

console.log('');
if (failures === 0) {
  console.log('PASS  all repo-level checks passed');
  process.exit(0);
}
console.log(`FAIL  ${failures} check(s) failed`);
process.exit(1);
