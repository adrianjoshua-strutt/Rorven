import { expect, test } from "@playwright/test";

test.describe("Rorven console", () => {
  test("routes between root, settings, and a real project", async ({ page }, testInfo) => {
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
    const createResponse = await page.request.post("http://127.0.0.1:8000/projects", {
      data: {
        name: projectName,
        allowed_root: allowedRoot,
        workspace_root: workspaceRoot,
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const created = await createResponse.json();
    const projectId = created.project.id as string;

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Root project" })).toBeVisible();
    await expect(page.getByText("Subagent activity")).toBeVisible();
    await expect(page).toHaveURL(/#\/root$/);

    await page.getByRole("button", { name: /^Settings/ }).click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
    await expect(page).toHaveURL(/#\/settings$/);
    await expect(page.getByText("Model tiers")).toBeVisible();
    await expect(page.getByText("Project defaults")).toBeVisible();
    await expect(page.getByText("Secret visibility")).toHaveCount(0);
    await expect(page.getByText("Memory backend")).toHaveCount(0);

    await page.getByRole("navigation", { name: "Projects" }).getByRole("button", { name: projectName }).click();
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`#\\/projects\\/${projectId}$`));
    await expect(page.getByPlaceholder("Message the project orchestrator")).toBeVisible();

    await page.reload();
    await expect(page.getByRole("button", { name: /^Root project/ })).toBeVisible();
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();
    await page.getByRole("button", { name: /^Root project/ }).click();
    await expect(page.getByRole("heading", { name: "Root project" })).toBeVisible();
    await page.goBack();
    await expect(page.getByRole("heading", { name: projectName })).toBeVisible();

    await page.getByPlaceholder("Message the project orchestrator").fill("Create a durable test run");
    await page.keyboard.press("Shift+Enter");
    await expect(page.getByText("Create a durable test run")).toBeVisible();
    await expect(page.getByText(/Working|Queued|Done/)).toBeVisible();

    await page.getByPlaceholder("Message the project orchestrator").fill("Add a second durable request");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("Create a durable test run")).toBeVisible();
    await expect(page.getByText("Add a second durable request")).toBeVisible();

    expect(consoleErrors).toEqual([]);
  });
});
