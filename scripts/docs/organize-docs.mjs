#!/usr/bin/env node
/**
 * Consolidate Markdown docs into /docs with a clean IA.
 * - Creates target files if missing.
 * - Appends/merges known sources into target sections.
 * - Rewrites relative links to new locations.
 * - Prints a diff-like summary (no destructive deletes; you remove old files in PR).
 */
import fs from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const docsDir = path.join(repoRoot, "docs");

const plan = [
  {
    target: "TESTING.md",
    heading: "# Testing",
    merge: [
      { from: "docs/TEST_EXECUTION_SUMMARY.md", as: "## Confidence Learning Test Summary" },
    ],
  },
  {
    target: "SECURITY.md",
    heading: "# Security",
    merge: [
      { from: "docs/SECURITY_UI_QUICKSTART.md", as: "## Security UI Quickstart" },
    ],
  },
  {
    target: "BACKEND.md",
    heading: "# Backend",
    merge: [
      { from: "docs/BACKEND_IMPLEMENTATION_COMPLETE.md", as: "## Implementation Summary" },
    ],
  },
  {
    target: "FRONTEND.md",
    heading: "# Frontend",
    merge: [
      { from: "docs/ADMIN_CONTROLS.md", as: "## Admin Controls & Overlay" },
    ],
  },
  {
    target: "OPS.md",
    heading: "# Operations",
    merge: [
      { from: "docs/DEPLOYMENT_VERIFICATION.md", as: "## Deployment Verification Playbook" },
    ],
  },
];

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function readOrEmpty(p) {
  return fs.existsSync(p) ? fs.readFileSync(p, "utf8") : "";
}

function normalizeNewlines(s) {
  return s.replace(/\r\n/g, "\n").trim() + "\n";
}

function appendSection(content, sectionTitle, body) {
  const sep = content.endsWith("\n") ? "" : "\n";
  return `${content}${sep}\n${sectionTitle}\n\n${body.trim()}\n`;
}

function rewriteLinks(md, mapping) {
  // naive rewrite: if a link contains old path, swap with new guessed location
  let out = md;
  for (const [oldRel, newRel] of Object.entries(mapping)) {
    const pattern = new RegExp(`\\]\\((?:\\./)?${oldRel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\)`, "g");
    out = out.replace(pattern, `](${newRel})`);
  }
  return out;
}

function run() {
  ensureDir(docsDir);

  // mapping for simple link rewrites (source→target)
  const linkMap = {
    "TEST_EXECUTION_SUMMARY.md": "TESTING.md",
    "SECURITY_UI_QUICKSTART.md": "SECURITY.md",
    "BACKEND_IMPLEMENTATION_COMPLETE.md": "BACKEND.md",
    "ADMIN_CONTROLS.md": "FRONTEND.md",
    "DEPLOYMENT_VERIFICATION.md": "OPS.md",
  };

  const summary = [];

  for (const step of plan) {
    const targetPath = path.join(docsDir, step.target);
    let content = readOrEmpty(targetPath);
    if (!content) content = step.heading + "\n\n";

    for (const m of step.merge) {
      const sourcePath = path.join(repoRoot, m.from);
      if (!fs.existsSync(sourcePath)) {
        summary.push(`SKIP ${m.from} → ${step.target} (not found)`);
        continue;
      }
      let body = readOrEmpty(sourcePath);
      body = rewriteLinks(body, linkMap);
      content = appendSection(content, m.as, body);
      summary.push(`MERGE ${m.from} → ${step.target} :: "${m.as}"`);
    }

    content = normalizeNewlines(content);
    fs.writeFileSync(targetPath, content, "utf8");
  }

  // Create docs/README.md (TOC)
  const toc = [
    "# ApplyLens Documentation",
    "",
    "## Table of Contents",
    "- [Overview](./OVERVIEW.md)",
    "- [Getting Started](./GETTING_STARTED.md)",
    "- [Architecture](./ARCHITECTURE.md)",
    "- [Backend](./BACKEND.md)",
    "- [Frontend](./FRONTEND.md)",
    "- [Search & Elasticsearch](./SEARCH_ES.md)",
    "- [Security](./SECURITY.md)",
    "- [Testing](./TESTING.md)",
    "- [Operations](./OPS.md)",
    "- [Release Process](./RELEASE.md)",
    "- [Changelog](./CHANGELOG.md)",
    "- [Contributing](./CONTRIBUTING.md)",
    "",
  ].join("\n");
  fs.writeFileSync(path.join(docsDir, "README.md"), toc, "utf8");

  console.log("Docs consolidation summary:");
  for (const line of summary) console.log(" -", line);

  console.log("\nNext steps:");
  console.log(" 1) Review new files under /docs");
  console.log(" 2) Delete superseded originals once you're satisfied");
  console.log(" 3) Commit changes");
}

run();
