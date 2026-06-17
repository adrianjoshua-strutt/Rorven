import { expect, test } from "@playwright/test";

test.describe("Rorven console", () => {
  test("creates and reopens a project through the real UI", async ({ page }, testInfo) => {
    const consoleErrors: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error") {
        consoleErrors.push(message.text());
      }
    });
    page.on("pageerror", (error) => {
      consoleErrors.push(error.message);
    });

    const suffix = `${testInfo.project.name}-${Date.now()}`;
    const projectName = `PW ${suffix}`;
    const allowedRoot = `D:/Cloud/Dropbox/GitHub/rorven/test-output/playwright-ui/workspaces`;
    const workspaceRoot = `${allowedRoot}/${suffix}`;

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Root project" })).toBeVisible();
    await expect(page.getByText("Subagent activity")).toBeVisible();

    await page.getByRole("button", { name: /^Settings/ }).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    await expect(page.getByText("Model provider API key")).toBeVisible();

    await page.getByRole("button", { name: /^Project$/ }).click();
    await expect(page.getByRole("dialog", { name: "Create project" })).toBeVisible();
    await page.getByLabel("Name").fill(projectName);
    await page.getByLabel("Allowed root").fill(allowedRoot);
    await page.getByLabel("Workspace root").fill(workspaceRoot);
    await page.getByRole("button", { name: "Create project" }).click();

    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Projects" }).getByText(projectName)).toBeVisible();
    await expect(page.getByPlaceholder("Message the project orchestrator")).toBeVisible();

    await page.reload();
    await expect(page.getByRole("button", { name: /^Root project/ })).toBeVisible();
    await page.getByRole("navigation", { name: "Projects" }).getByText(projectName).click();
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();

    await page.getByPlaceholder("Message the project orchestrator").fill("Create a durable test run");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("Create a durable test run")).toBeVisible();
    await expect(page.getByText(/Working|Queued|Done/)).toBeVisible();

    await page.getByPlaceholder("Message the project orchestrator").fill("Add a second durable request");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("Create a durable test run")).toBeVisible();
    await expect(page.getByText("Add a second durable request")).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });
});
