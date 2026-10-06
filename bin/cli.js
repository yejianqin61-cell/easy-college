#!/usr/bin/env node
/**
 * easy-college — install the skills in this package into your agent's skills directory.
 *
 *   npx easy-college                 install every skill (skips ones already present)
 *   npx easy-college --list          print the skill names
 *   npx easy-college --force         reinstall, overwriting existing skills
 *   npx easy-college --dest <dir>    install somewhere else
 */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(path.resolve(HERE, '..'), 'skills');

const args = process.argv.slice(2);
const has = (name) => args.includes(name);
const valueOf = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};

function usage() {
  console.log(`
easy-college — courseware to study notes, as agent skills.

Usage
  npx easy-college [options]

Options
  --list             print the skill names and exit
  --dest <dir>       install into <dir> (default: ~/.agents/skills)
  --force            overwrite skills that are already installed
  -h, --help         show this message

After installing, ask your agent to turn a lecture into notes — for example
"turn this PDF into study notes" — and the easy-learning skill takes over.
`);
}

if (has('-h') || has('--help')) {
  usage();
  process.exit(0);
}

if (!fs.existsSync(SRC)) {
  console.error(`skills/ not found next to this script (${SRC}).`);
  process.exit(1);
}

const names = fs
  .readdirSync(SRC, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();

if (has('--list')) {
  for (const name of names) console.log(name);
  process.exit(0);
}

const dest = path.resolve(valueOf('--dest') || path.join(os.homedir(), '.agents', 'skills'));
const force = has('--force');

/**
 * Remove whatever sits at `target` without ever following a link into it.
 * A skill installed as a junction or symlink must be unlinked, not recursed
 * into — recursing would delete the directory the link points at.
 */
function removeOnly(target) {
  let stat;
  try {
    stat = fs.lstatSync(target);
  } catch {
    return;
  }
  if (stat.isSymbolicLink()) fs.unlinkSync(target);
  else fs.rmSync(target, { recursive: true, force: true });
}

fs.mkdirSync(dest, { recursive: true });

let installed = 0;
let skipped = 0;

for (const name of names) {
  const target = path.join(dest, name);
  if (fs.existsSync(target) && !force) {
    console.log(`skip    ${name}  (already at ${target} — use --force to replace)`);
    skipped += 1;
    continue;
  }
  removeOnly(target);
  fs.cpSync(path.join(SRC, name), target, { recursive: true });
  console.log(`install ${name}  ->  ${target}`);
  installed += 1;
}

console.log(
  `\n${installed} installed, ${skipped} skipped. Skills directory: ${dest}` +
    (skipped ? '\nRe-run with --force to overwrite the skipped ones.' : '')
);
