import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
async function connect(page: Page) {
  await page.goto("/");
  await expect(
    page.getByText("Stream connected", { exact: true }),
  ).toBeVisible();
}
async function load(page: Page, scenario: string) {
  if (!(await page.getByLabel("Scenario", { exact: true }).isVisible())) {
    await page
      .getByRole("button", { name: "Scenario studio", exact: true })
      .click();
  }
  await page.getByLabel("Scenario", { exact: true }).selectOption(scenario);
  await page
    .getByRole("button", { name: "Load raw scenario", exact: true })
    .click();
  const confirm = page.getByRole("button", {
    name: "Reset replay and load scenario",
  });
  if (await confirm.isVisible()) await confirm.click();
  await expect(page.locator(".status-banner")).toContainText(
    "Replay completed",
    { timeout: 90000 },
  );
}
test("scenario → graph / map / media → claim review → verified export", async ({
  page,
}, info) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const remote: string[] = [];
  page.on("request", (request) => {
    if (
      !request.url().startsWith("http://127.0.0.1") &&
      !request.url().startsWith("blob:") &&
      !request.url().startsWith("data:")
    )
      remote.push(request.url());
  });
  await connect(page);
  await load(page, "cmp_electoral_01");
  await page
    .getByRole("button", { name: "Scenario studio", exact: true })
    .click();
  await expect(page.getByLabel("Scenario", { exact: true })).not.toBeVisible();
  await page
    .getByLabel("Search campaigns")
    .fill("a-narrative-that-does-not-exist");
  await expect(page.locator(".campaign-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Clear campaign filters" }).click();
  await expect(page.locator(".campaign-card")).not.toHaveCount(0);
  await page.getByRole("button", { name: "Warnings", exact: true }).click();
  await expect(page.locator(".campaign-card.active")).toBeVisible();
  await page.getByRole("button", { name: "All cases", exact: true }).click();
  await page.getByRole("button", { name: "Inspect strongest link" }).click();
  await expect(page.locator(".inspector h2")).toHaveText("CO POST SYNC");
  await expect(
    page.getByRole("heading", { name: "Exact matched event IDs" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await page.getByRole("button", { name: "Open account evidence" }).click();
  await expect(page.locator(".inspector")).toContainText(
    "global origin is not established",
  );
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await page.getByRole("button", { name: "Review claim evidence" }).click();
  await expect(
    page.getByRole("tab", { name: "Claims", exact: true }),
  ).toBeFocused();
  await expect(
    page.getByRole("tab", { name: "Claims", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await page.getByRole("tab", { name: "Graph", exact: true }).click();
  await page.locator(".assessment-explanation summary").click();
  await expect(page.getByText(/Missing components:/)).toBeVisible();
  await page.locator(".assessment-explanation summary").click();
  await expect(page.getByLabel("Recent local warning markers")).toBeVisible();
  await expect(page.getByLabel("Recent local warning markers")).toContainText(
    "12:",
  );
  await expect(
    page.getByRole("heading", { name: "Coordination graph", exact: true }),
  ).toBeVisible();
  await page.locator(".node-list button").first().click();
  await expect(page.locator(".inspector h2")).toBeVisible();
  await page.screenshot({ path: info.outputPath("graph.png"), fullPage: true });
  await page.getByRole("button", { name: "Clear", exact: true }).click();
  await page.getByRole("tab", { name: "Geography", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Geographic context", exact: true }),
  ).toBeVisible();
  await page.locator(".geo-cells button").first().click();
  await page.screenshot({ path: info.outputPath("map.png"), fullPage: true });
  await page.getByRole("button", { name: "Clear cross-filters" }).click();
  await page.getByRole("tab", { name: "Media", exact: true }).click();
  await expect(page.getByAltText("Computed ELA heatmap")).toHaveAttribute(
    "src",
    /^blob:/,
  );
  await page.getByLabel("ELA comparison split").focus();
  await page.keyboard.press("ArrowRight");
  await page.screenshot({ path: info.outputPath("media.png"), fullPage: true });
  await page.getByRole("tab", { name: "Claims", exact: true }).click();
  await expect(page.getByText(/SYNTHETIC DEMO ADVISORY —/)).toBeVisible();
  await page
    .getByLabel("Contextual note")
    .fill(
      "Reviewed the fictional advisory date and Lucknow region; media context remains incomplete.",
    );
  await page.getByRole("button", { name: "Save authenticated review" }).click();
  await expect(page.getByText(/Reviewed by local-analyst:/)).toBeVisible();
  await page
    .getByRole("button", { name: "Export dossier", exact: true })
    .click();
  await page.getByRole("button", { name: "Queue verified export" }).click();
  await expect(
    page.getByRole("button", { name: "Download completed ZIP", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  const pending = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download completed ZIP", exact: true })
    .click();
  const download = await pending;
  const output = info.outputPath("dossier.zip");
  await download.saveAs(output);
  const python =
    process.env.PW_PYTHON ??
    (process.platform === "win32"
      ? resolve("../.venv/Scripts/python.exe")
      : resolve("../.venv/bin/python"));
  execFileSync(python, [
    "-c",
    "import sys,json,hashlib,zipfile; z=zipfile.ZipFile(sys.argv[1]); m=json.loads(z.read('manifest.json')); assert all(hashlib.sha256(z.read(n)).hexdigest()==v['sha256'] for n,v in m['files'].items()); assert z.read('report.pdf').startswith(b'%PDF')",
    output,
  ]);
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("tab", { name: "Graph", exact: true }).click();
  await page.screenshot({
    path: info.outputPath("narrow.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
  expect(remote).toEqual([]);
});
test("injected origin survives replay reset and reconnect restores snapshots", async ({
  page,
}, info) => {
  await connect(page);
  await page.getByRole("button", { name: "Inject event", exact: true }).click();
  await page
    .getByLabel("Observed text")
    .fill("परीक्षण: independent local observation for injection journey.");
  await page.getByLabel("Language", { exact: true }).selectOption("hi");
  await page
    .getByRole("button", { name: "Queue injection", exact: true })
    .click();
  await expect(page.getByRole("dialog")).not.toBeVisible({ timeout: 30000 });
  const injectedCount = await page
    .locator(".campaign-card")
    .filter({ hasText: "USER INJECTED" })
    .count();
  expect(injectedCount).toBeGreaterThan(0);
  await load(page, "cmp_geo_astroturf_02");
  await page.getByRole("tab", { name: "Geography", exact: true }).click();
  await expect(
    page.getByText(/Coordination-gated geographic mismatch indicator/),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("geo-mismatch.png"),
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Use local WebGL map", exact: true })
    .click();
  await expect(
    page.locator(".webgl-map canvas, .offline-map").first(),
  ).toBeVisible();
  await page.screenshot({
    path: info.outputPath("webgl-or-fallback.png"),
    fullPage: true,
  });
  await expect(
    page.locator(".campaign-card").filter({ hasText: "USER INJECTED" }),
  ).toHaveCount(injectedCount);
  await page.evaluate(() => {
    for (const key of Object.keys(localStorage))
      if (/token/i.test(key))
        throw new Error("Session token persisted in browser storage");
  });
  // Reload opens the workbench directly and resynchronizes persisted snapshots.
  await page.reload();
  await expect(
    page.getByText("Stream connected", { exact: true }),
  ).toBeVisible();
  await expect(
    page.locator(".campaign-card").filter({ hasText: "USER INJECTED" }),
  ).toHaveCount(injectedCount);
});

test("natural discussion stays suppressed and a dropped stream reconnects", async ({
  page,
}, info) => {
  await page.addInitScript(() => {
    const NativeSocket = window.WebSocket;
    window.WebSocket = class extends NativeSocket {
      constructor(url: string | URL, protocols?: string | string[]) {
        super(url, protocols);
        (window as Window & { journeySocket?: WebSocket }).journeySocket = this;
      }
    };
  });
  let connections = 0;
  page.on("websocket", () => connections++);
  await connect(page);
  await page.evaluate(() => {
    (window as Window & { journeySocket?: WebSocket }).journeySocket?.close(
      4000,
      "Journey test: connection interruption",
    );
  });
  await expect(page.getByText(/Reconnecting in/)).toBeVisible();
  await expect(
    page.getByText("Stream connected", { exact: true }),
  ).toBeVisible();
  expect(connections).toBeGreaterThanOrEqual(2);
  await load(page, "cmp_organic_03");
  await expect(page.getByText(/Alert suppressed:/)).toBeVisible();
  await expect(page.getByLabel("Recent local warning markers")).toHaveCount(0);
  await page.getByRole("button", { name: "Warnings", exact: true }).click();
  await expect(page.locator(".campaign-card")).toHaveCount(0);
  await page.getByRole("button", { name: "All cases", exact: true }).click();
  await expect(
    page.getByRole("button", {
      name: "Mask low-indicator and unclassified identities",
    }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({
    path: info.outputPath("natural-discussion.png"),
    fullPage: true,
  });
});
