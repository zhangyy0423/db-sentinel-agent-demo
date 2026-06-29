import { existsSync, mkdirSync } from "node:fs";
import { basename, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const outputDir = "/tmp/db-sentinel-doc-images";
const assets = [
  "docs/assets/system-overview.svg",
  "docs/assets/agent-workflow.svg",
  "docs/assets/safety-shield.svg",
  "docs/assets/demo-storyboard.svg",
  "docs/assets/value-map.svg"
];

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function launchBrowser() {
  if (existsSync(chromePath)) {
    return chromium.launch({ executablePath: chromePath, headless: true });
  }
  return chromium.launch({ channel: "chrome", headless: true });
}

mkdirSync(outputDir, { recursive: true });

const browser = await launchBrowser();
const outputs = [];
try {
  for (const asset of assets) {
    assert(existsSync(asset), `missing SVG asset: ${asset}`);
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    await page.goto(pathToFileURL(resolve(asset)).toString(), { waitUntil: "load" });
    const size = await page.evaluate(() => {
      const svg = document.querySelector("svg");
      if (!svg) {
        return null;
      }
      const rect = svg.getBoundingClientRect();
      return { width: Math.round(rect.width), height: Math.round(rect.height) };
    });
    assert(size && size.width > 1000 && size.height > 500, `unexpected SVG render size for ${asset}`);
    const out = `${outputDir}/${basename(asset, ".svg")}.png`;
    await page.screenshot({
      path: out,
      clip: { x: 0, y: 0, width: 1280, height: 720 },
      timeout: 10000
    });
    outputs.push(out);
    await page.close();
  }
} finally {
  await browser.close();
}

console.log(
  JSON.stringify(
    {
      rendered: outputs.length,
      outputs
    },
    null,
    2
  )
);
