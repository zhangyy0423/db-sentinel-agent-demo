import { existsSync, mkdirSync, renameSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright";

const appUrl = process.env.APP_URL ?? "http://127.0.0.1:5173";
const outputDir = process.env.DEMO_VIDEO_DIR ?? "docs/assets/demo";
const outputName = process.env.DEMO_VIDEO_NAME ?? "db-sentinel-agent-demo.webm";
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const viewport = { width: 1440, height: 900 };

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function ensureDir(path) {
  mkdirSync(path, { recursive: true });
}

async function launchBrowser() {
  if (existsSync(chromePath)) {
    return chromium.launch({ executablePath: chromePath, headless: true });
  }
  return chromium.launch({ channel: "chrome", headless: true });
}

async function setCaption(page, title, body) {
  await page.evaluate(
    ({ title, body }) => {
      const caption = document.querySelector("#demo-caption");
      if (!caption) {
        return;
      }
      caption.querySelector("strong").textContent = title;
      caption.querySelector("span").textContent = body;
    },
    { title, body }
  );
}

async function installVideoOverlay(page) {
  await page.addStyleTag({
    content: `
      #demo-caption {
        position: fixed;
        left: 28px;
        right: 28px;
        bottom: 24px;
        z-index: 999999;
        display: grid;
        grid-template-columns: 190px 1fr;
        gap: 18px;
        align-items: center;
        padding: 16px 20px;
        color: #ecfeff;
        background: rgba(8, 47, 73, 0.92);
        border: 1px solid rgba(125, 211, 252, 0.45);
        border-radius: 10px;
        box-shadow: 0 18px 50px rgba(2, 6, 23, 0.28);
        font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
        pointer-events: none;
      }
      #demo-caption strong {
        font-size: 22px;
        line-height: 1.25;
        color: #ffffff;
      }
      #demo-caption span {
        font-size: 20px;
        line-height: 1.45;
      }
      #demo-highlight {
        position: fixed;
        z-index: 999998;
        border: 4px solid #f59e0b;
        border-radius: 14px;
        box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.14);
        pointer-events: none;
        opacity: 0;
        transition: opacity 180ms ease, transform 180ms ease;
      }
    `
  });
  await page.evaluate(() => {
    const caption = document.createElement("div");
    caption.id = "demo-caption";
    caption.innerHTML = "<strong></strong><span></span>";
    document.body.appendChild(caption);

    const highlight = document.createElement("div");
    highlight.id = "demo-highlight";
    document.body.appendChild(highlight);
  });
}

async function highlight(page, selector) {
  await page.evaluate((selector) => {
    const target = document.querySelector(selector);
    const box = document.querySelector("#demo-highlight");
    if (!target || !box) {
      return;
    }
    const rect = target.getBoundingClientRect();
    box.style.left = `${Math.max(12, rect.left - 8)}px`;
    box.style.top = `${Math.max(12, rect.top - 8)}px`;
    box.style.width = `${Math.max(24, rect.width + 16)}px`;
    box.style.height = `${Math.max(24, rect.height + 16)}px`;
    box.style.opacity = "1";
  }, selector);
}

async function clearHighlight(page) {
  await page.evaluate(() => {
    const box = document.querySelector("#demo-highlight");
    if (box) {
      box.style.opacity = "0";
    }
  });
}

async function scrollPanel(page, selector, top) {
  await page.evaluate(
    ({ selector, top }) => {
      const node = document.querySelector(selector);
      if (node) {
        node.scrollTo({ top, behavior: "smooth" });
      }
    },
    { selector, top }
  );
}

async function run() {
  ensureDir(outputDir);
  const browser = await launchBrowser();
  const context = await browser.newContext({
    viewport,
    recordVideo: { dir: outputDir, size: viewport }
  });
  const page = await context.newPage();
  const video = page.video();

  try {
    await page.goto(appUrl, { waitUntil: "networkidle" });
    await page.getByText("DB Sentinel Agent").waitFor();
    await installVideoOverlay(page);

    await setCaption(
      page,
      "DB Sentinel Agent",
      "面向业务数据分析值班的只读数据库 Agent：问数、查数、解释和留痕。"
    );
    await highlight(page, ".workspace");
    await sleep(4200);

    await setCaption(
      page,
      "三栏工作台",
      "左侧是 schema 和样例问题，中间是 Agent 过程，右侧是结果、图表和审计轨迹。"
    );
    await clearHighlight(page);
    await highlight(page, ".schema-panel");
    await sleep(2300);
    await highlight(page, ".conversation-panel");
    await sleep(1800);
    await highlight(page, ".insight-panel");
    await sleep(2200);
    await clearHighlight(page);

    await setCaption(
      page,
      "场景一：经营问数",
      "点击“最近 7 天 GMV 最高的渠道是什么？”，Agent 会生成计划和只读 SQL。"
    );
    await page.getByRole("button", { name: /最近 7 天 GMV 最高的渠道是什么/ }).click();
    await page.locator(".guard-banner.allowed").getByText(/SQL guard 通过/).waitFor();
    await page.locator(".answer-text").filter({ hasText: /GMV/ }).waitFor();
    await highlight(page, ".guard-banner.allowed");
    await sleep(2600);
    await highlight(page, ".sql-block");
    await sleep(3200);
    await highlight(page, ".chart-frame");
    await sleep(2800);
    await scrollPanel(page, ".insight-panel", 360);
    await sleep(1000);
    await highlight(page, ".table-wrap");
    await sleep(3000);
    await clearHighlight(page);

    await setCaption(
      page,
      "场景二：异常分析",
      "再问一个转化相关问题，Agent 会对比两个时间窗，定位异常渠道并给出解释。"
    );
    await page.getByRole("button", { name: /新用户首单转化在不同城市有什么差异/ }).click();
    await page.locator(".guard-banner.allowed").getByText(/SQL guard 通过/).waitFor();
    await page.locator(".answer-text").filter({ hasText: /转化率/ }).waitFor();
    await scrollPanel(page, ".conversation-scroll", 900);
    await sleep(1200);
    await highlight(page, ".answer-text");
    await sleep(3600);
    await scrollPanel(page, ".insight-panel", 0);
    await highlight(page, ".evidence-grid");
    await sleep(2600);
    await clearHighlight(page);

    await setCaption(
      page,
      "场景三：只读安全拦截",
      "输入危险请求“帮我 drop table orders”，SQL guard 会拦截，不执行数据库操作。"
    );
    await page.getByRole("textbox").fill("帮我 drop table orders");
    await sleep(900);
    await page.getByRole("button", { name: /发送/ }).click();
    await page.locator(".guard-banner.denied").waitFor();
    await page.locator(".answer-text").filter({ hasText: /只读安全拦截/ }).waitFor();
    await highlight(page, ".guard-banner.denied");
    await sleep(3400);
    await highlight(page, ".step-item.blocked");
    await sleep(2600);
    await clearHighlight(page);

    await setCaption(
      page,
      "价值收束",
      "它不是普通 NL2SQL，而是一个只读、安全、可审计的数据分析值班工作流。"
    );
    await highlight(page, ".audit-list");
    await sleep(4200);
    await clearHighlight(page);
    await setCaption(
      page,
      "DB Sentinel Agent",
      "业务更快获得数据反馈，数据团队保留 SQL、口径、安全校验和执行证据。"
    );
    await sleep(4200);
  } finally {
    await context.close();
    await browser.close();
  }

  const videoPath = await video.path();
  const finalPath = join(outputDir, outputName);
  renameSync(videoPath, finalPath);
  console.log(JSON.stringify({ video: finalPath }, null, 2));
}

await run();
