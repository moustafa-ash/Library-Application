const { chromium } = require("playwright-core");
const assert = require("node:assert/strict");
const base = process.argv[2];
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);

(async () => {
    const browser = await chromium.launch({ channel: "chrome", headless: true });
    try {
        const page = await browser.newPage();
        const errors = [];
        page.on("pageerror", error => errors.push(error.message));
        for (const width of [1366, 360]) {
            await page.setViewportSize({ width, height: 900 });
            for (const route of ["login", "register"]) {
                await page.goto(`${base}/${route}`);
                for (const theme of ["light", "dark"]) {
                    if (await page.locator("html").getAttribute("data-theme") !== theme)
                        await page.locator("#theme-toggle").click();
                    const layout = await page.evaluate(() => ({
                        viewport: innerWidth,
                        document: document.documentElement.scrollWidth,
                        controls: [...document.querySelectorAll('button,input:not([type="hidden"])')]
                            .map(element => element.getBoundingClientRect().height),
                    }));
                    assert.ok(layout.document <= layout.viewport, `${route} overflows at ${width}px`);
                    assert.ok(layout.controls.every(height => height >= 44), "Control smaller than 44px");
                    assert.equal(await page.locator("html").getAttribute("data-theme"), theme);
                }
            }
        }
        await page.reload();
        assert.equal(await page.locator("html").getAttribute("data-theme"), "dark");
        const noJS = await browser.newContext({ javaScriptEnabled: false });
        const fallback = await noJS.newPage();
        await fallback.goto(`${base}/login`);
        assert.ok(await fallback.locator('input[name="csrf_token"]').getAttribute("value"));
        assert.equal(await fallback.locator("#theme-toggle").isVisible(), false);
        await noJS.close();
        const blockedStorage = await browser.newContext();
        await blockedStorage.addInitScript(() => {
            Storage.prototype.getItem = Storage.prototype.setItem = () => { throw new Error("Storage blocked"); };
        });
        const privatePage = await blockedStorage.newPage();
        privatePage.on("pageerror", error => errors.push(error.message));
        await privatePage.goto(`${base}/login`);
        await privatePage.getByRole("button", { name: "Switch to dark mode" }).click();
        assert.equal(await privatePage.locator("html").getAttribute("data-theme"), "dark");
        await blockedStorage.close();
        assert.deepEqual(errors, []);
        console.log("PASS: desktop/mobile, both themes, persistence, no-JavaScript forms, blocked storage, and no JavaScript errors.");
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exit(1); });
