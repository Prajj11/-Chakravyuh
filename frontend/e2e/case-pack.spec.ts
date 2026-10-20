import { test, expect } from "@playwright/test";

test("diverse case catalogue loads a real computed case in batch mode", async ({
  page,
}, info) => {
  // Optional local proxy lets this journey use an isolated backend while a user's dev UI runs.
  const proxy = process.env.PW_API_PROXY;
  if (proxy) {
    await page.route("http://127.0.0.1:8001/**", async (route) => {
      const url = route.request().url().replace("http://127.0.0.1:8001", proxy);
      const response = await route.fetch({ url });
      await route.fulfill({ response });
    });
    await page.addInitScript((origin) => {
      const NativeSocket = window.WebSocket;
      window.WebSocket = class extends NativeSocket {
        constructor(url: string | URL, protocols?: string | string[]) {
          super(
            String(url).replace(
              "ws://127.0.0.1:8001",
              origin.replace("http", "ws"),
            ),
            protocols,
          );
        }
      };
    }, proxy);
  }
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByText("Stream connected", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Scenario studio", exact: true })
    .click();
  const scenario = page.getByLabel("Scenario", { exact: true });
  await expect(scenario.locator("optgroup option")).toHaveCount(25);
  await scenario.selectOption("expanded");
  await expect(
    page.getByText("25 fictional cases · 7,500 posts · 1,500 accounts.", {
      exact: false,
    }),
  ).toBeVisible();
  const batch = page.getByLabel("Fast batch load (skip playback delays)");
  await expect(batch).toBeChecked();
  await expect(
    page.getByRole("combobox", { name: "Speed", exact: true }),
  ).toBeDisabled();
  await scenario.selectOption("demo_flood_photo");
  await page
    .getByRole("button", { name: "Load raw scenario", exact: true })
    .click();
  const confirm = page.getByRole("button", {
    name: "Reset replay and load scenario",
  });
  if (await confirm.isVisible()) await confirm.click();
  await expect(page.locator(".status-banner")).toContainText(
    "Replay completed",
    { timeout: 120000 },
  );
  await expect(page.locator(".campaign-card").first()).toContainText(
    "SYNTHETIC REPLAY",
  );
  await expect(
    page.getByRole("heading", { name: "Coordination graph", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".campaign-header")).toContainText(
    "SYNTHETIC EXERCISE",
  );
  await page.getByLabel("Search campaigns").fill("Mumbai");
  await expect(page.locator(".campaign-card").first()).toContainText("Mumbai");
  await page.getByLabel("Search campaigns").fill("");
  await page.screenshot({
    path: info.outputPath("case-pack-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth + 1,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: info.outputPath("case-pack-mobile.png"),
    fullPage: true,
  });
  await scenario.selectOption("cmp_electoral_01");
  await expect(batch).not.toBeChecked();
  await expect(
    page.getByRole("combobox", { name: "Speed", exact: true }),
  ).toBeEnabled();
  expect(errors).toEqual([]);
});
