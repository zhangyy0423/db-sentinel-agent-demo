import { existsSync, mkdirSync } from "node:fs";
import { chromium } from "playwright";

const appUrl = process.env.APP_URL ?? "http://127.0.0.1:5173";
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const screenshotDir = process.env.SCREENSHOT_DIR ?? "docs/assets/screenshots";

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

const browser = await launchBrowser();
try {
  mkdirSync(screenshotDir, { recursive: true });
  const desktop = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  await desktop.goto(appUrl, { waitUntil: "networkidle" });
  await desktop.getByText("DB Sentinel Agent").waitFor();
  await desktop.getByRole("heading", { name: "Schema" }).waitFor();
  await desktop.getByRole("heading", { name: "Agent Console" }).waitFor();
  await desktop.getByRole("heading", { name: "Result & Audit" }).waitFor();
  await desktop.screenshot({ path: `${screenshotDir}/workbench.png`, fullPage: true });

  await desktop.getByRole("button", { name: /最近 7 天 GMV 最高的渠道是什么/ }).click();
  await desktop.locator(".guard-banner.allowed").getByText(/SQL guard 通过/).waitFor();
  await desktop.locator(".answer-text").filter({ hasText: /GMV 为/ }).waitFor();
  await desktop.locator(".recharts-surface").first().waitFor();
  const tableRows = await desktop.locator(".table-wrap tbody tr").count();
  assert(tableRows > 0, "样例问题没有渲染结果表格");
  await desktop.locator(".evidence-item").filter({ hasText: /session_id/ }).waitFor();
  await desktop.screenshot({ path: `${screenshotDir}/gmv-result.png`, fullPage: true });

  await desktop.getByRole("textbox").fill("帮我 drop table orders");
  await desktop.getByRole("button", { name: /发送/ }).click();
  await desktop.locator(".answer-text").filter({ hasText: /只读安全拦截/ }).waitFor();
  await desktop.locator(".guard-banner.denied").waitFor();
  const staleAllowedBanners = await desktop.locator(".guard-banner.allowed").count();
  assert(staleAllowedBanners === 0, "危险请求完成后仍显示上一轮 green guard");
  await desktop.screenshot({ path: `${screenshotDir}/safety-block.png`, fullPage: true });
  await desktop.screenshot({ path: "/tmp/db-sentinel-desktop.png", fullPage: true });

  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await mobile.goto(appUrl, { waitUntil: "networkidle" });
  await mobile.getByText("DB Sentinel Agent").waitFor();
  const overflow = await mobile.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  assert(overflow <= 2, `移动端出现横向溢出：${overflow}px`);
  await mobile.screenshot({ path: `${screenshotDir}/mobile-workbench.png`, fullPage: true });
  await mobile.screenshot({ path: "/tmp/db-sentinel-mobile.png", fullPage: true });

  console.log(
    JSON.stringify(
      {
        desktop: "ok",
        sampleQuestion: "ok",
        dangerousRequest: "ok",
        mobileOverflowPx: overflow,
        screenshots: [
          `${screenshotDir}/workbench.png`,
          `${screenshotDir}/gmv-result.png`,
          `${screenshotDir}/safety-block.png`,
          `${screenshotDir}/mobile-workbench.png`,
          "/tmp/db-sentinel-desktop.png",
          "/tmp/db-sentinel-mobile.png"
        ]
      },
      null,
      2
    )
  );
} finally {
  await browser.close();
}
