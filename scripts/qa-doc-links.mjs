import { existsSync, readFileSync } from "node:fs";
import { dirname, extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = normalize(join(dirname(fileURLToPath(import.meta.url)), ".."));
const docs = [
  "README.md",
  "docs/README.md",
  "docs/PROJECT_OVERVIEW.md",
  "docs/COMPETITION_SUBMISSION.md",
  "docs/ONE_PAGER.md",
  "docs/PITCH_DECK_OUTLINE.md",
  "docs/VIDEO_SCRIPT.md",
  "docs/DEMO_GUIDE.md",
  "docs/ARCHITECTURE.md",
  "docs/CONFIGURATION.md",
  "docs/SUBMISSION_CHECKLIST.md",
  "docs/JUDGE_QA.md"
];
const linkPattern = /!?\[[^\]]*]\(([^)\s]+)(?:\s+"[^"]*")?\)/g;
const missing = [];

for (const doc of docs) {
  const absDoc = join(rootDir, doc);
  if (!existsSync(absDoc)) {
    missing.push(`${doc}: document missing`);
    continue;
  }

  const content = readFileSync(absDoc, "utf8");
  for (const match of content.matchAll(linkPattern)) {
    const href = match[1];
    if (
      href.startsWith("http://") ||
      href.startsWith("https://") ||
      href.startsWith("#") ||
      href.startsWith("mailto:")
    ) {
      continue;
    }
    const cleanHref = href.split("#", 1)[0];
    if (!cleanHref || extname(cleanHref) === "") {
      continue;
    }
    const target = normalize(join(dirname(absDoc), cleanHref));
    if (!target.startsWith(rootDir) || !existsSync(target)) {
      missing.push(`${doc}: ${href}`);
    }
  }
}

if (missing.length) {
  throw new Error(`Missing local doc links:\n${missing.join("\n")}`);
}

console.log(JSON.stringify({ checked: docs.length, missing: 0 }, null, 2));
