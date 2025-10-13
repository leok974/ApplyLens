#!/usr/bin/env node
/**
 * Adds a language to bare triple-backtick code fences across all Markdown files.
 * Heuristics:
 *  - JSON-looking blocks → json
 *  - INI-looking blocks  → ini
 *  - Shell/CLI snippets  → bash
 *  - Fallback            → text
 */
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const skip = new Set(["node_modules",".git",".venv",".mypy_cache",".pytest_cache",".idea",".vscode","htmlcov","coverage"]);

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
    const p = path.join(dir, d.name);
    if (d.isDirectory() && !skip.has(d.name)) return walk(p);
    return d.isFile() && p.toLowerCase().endsWith(".md") ? [p] : [];
  });
}

function guessLang(lines, i) {
  const peek = (lines[i+1] ?? "") + (lines[i+2] ?? "");
  if (/^\s*[{[]/.test(peek)) return "json";
  if (/^\s*\[.+?\]/.test(peek) || /(^|[\r\n])\s*\w+\s*=\s*.+/.test(peek)) return "ini";
  if (/\b(git|npm|pnpm|yarn|pip|pytest|curl|docker|kubectl|sed|awk|grep|bash|sh|powershell)\b/.test(peek) || /^\s*[$>]/m.test(peek)) return "bash";
  return "text";
}

const files = walk(root);
let changedCount = 0;

for (const file of files) {
  const src = fs.readFileSync(file, "utf8").split(/\r?\n/);
  let changed = false;
  for (let i = 0; i < src.length; i++) {
    if (/^```$/.test(src[i])) {
      src[i] = "```" + guessLang(src, i);
      changed = true;
    }
  }
  if (changed) {
    fs.writeFileSync(file, src.join("\n"));
    changedCount++;
    console.log("patched:", path.relative(root, file));
  }
}

console.log(`\nFence fixer complete. Patched ${changedCount} file(s).`);
