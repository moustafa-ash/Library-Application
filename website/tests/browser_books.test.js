const { chromium } = require('playwright-core');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const base = process.argv[2];
assert.match(base, /^http:\/\/127\.0\.0\.1:\d+$/);

(async () => {
    const browser = await chromium.launch({ channel: 'chrome', headless: true });
    try {
        const context = await browser.newContext();
        const page = await context.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.goto(`${base}/_books_test/login`);
        for (const width of [1366, 360]) {
            await page.setViewportSize({ width, height: 900 });
            for (const route of ['/books/', '/books/add', '/books/1/edit', '/books/1/delete',
                                 '/authors/', '/authors/add', '/authors/1/edit', '/authors/1/delete']) {
                await page.goto(base + route);
                for (const theme of ['light', 'dark']) {
                    if (await page.locator('html').getAttribute('data-theme') !== theme)
                        await page.locator('#theme-toggle').click();
                    assert.equal(await page.locator('html').getAttribute('data-theme'), theme);
                    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${route} overflows at ${width}`);
                    assert.ok(await page.locator('h1').isVisible());
                }
            }
        }
        await page.goto(`${base}/books/add`);
        await page.locator('#title').fill('Browser cover demonstration');
        await page.locator('#price').fill('42.50');
        await page.locator('#author_id').selectOption('1');
        await page.locator('#cover').setInputFiles({ name: 'cover.png', mimeType: 'image/png',
            buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==', 'base64') });
        await page.getByRole('button', { name: 'Save book' }).click();
        await page.waitForURL(`${base}/books/`);
        const row = page.getByRole('row').filter({ hasText: 'Browser cover demonstration' });
        await row.getByRole('link', { name: 'Edit Browser cover demonstration', exact: true }).click();
        const preview = page.locator('main img');
        await preview.waitFor();
        assert.ok(await preview.evaluate(image => image.complete && image.naturalWidth > 0));
        await page.locator('#title').focus();
        await page.keyboard.press('Tab');
        assert.equal(await page.locator('#price').evaluate(input => input === document.activeElement), true);
        const directory = path.resolve(__dirname, '../instance/book-checks');
        fs.mkdirSync(directory, { recursive: true });
        await page.screenshot({ path: path.join(directory, 'mobile-dark-edit.png'), fullPage: true });
        await page.setViewportSize({ width: 1366, height: 900 });
        await page.locator('#theme-toggle').click();
        await page.screenshot({ path: path.join(directory, 'desktop-light-edit.png'), fullPage: true });
        await preview.evaluate(image => { image.src = '/media/books/missing.jpg'; });
        await page.waitForSelector('main .image-fallback', { timeout: 3000 });
        assert.equal(await page.locator('main .image-fallback').textContent(), 'No cover');
        // Re-submit without a file: the existing JPEG must remain visible.
        await page.getByRole('button', { name: 'Save book' }).click();
        await page.waitForURL(`${base}/books/`);
        await row.getByRole('link', { name: 'Delete Browser cover demonstration', exact: true }).click();
        await page.getByRole('button', { name: 'Delete book', exact: true }).click();
        await page.waitForURL(`${base}/books/`);
        assert.equal(await row.count(), 0);

        // Author/photo CRUD and a book attached through the actual browser forms.
        const photo = { name: 'author.png', mimeType: 'image/png',
            buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWQAAAABJRU5ErkJggg==', 'base64') };
        await page.goto(`${base}/authors/add`);
        await page.locator('#name').fill('Browser author');
        await page.locator('#country').fill('Egypt');
        await page.locator('#photo').setInputFiles(photo);
        await page.getByRole('button', { name: 'Save author' }).click();
        await page.waitForURL(`${base}/authors/`);
        let authorRow = page.getByRole('row').filter({ hasText: 'Browser author' });
        const authorEdit = await authorRow.getByRole('link', { name: 'Edit', exact: true }).getAttribute('href');
        const authorId = authorEdit.match(/\/authors\/(\d+)\/edit$/)[1];
        await page.goto(base + authorEdit);
        let oldPhoto = await page.locator('main img').getAttribute('src');
        assert.ok(await page.locator('main img').evaluate(image => image.complete && image.naturalWidth > 0));
        await page.locator('main img').evaluate(image => { image.src = '/media/authors/missing.jpg'; });
        await page.waitForSelector('main .image-fallback', { timeout: 3000 });
        assert.equal(await page.locator('main .image-fallback').textContent(), 'No photo');
        await page.getByRole('button', { name: 'Save author' }).click();
        await page.waitForURL(`${base}/authors/`);
        await page.goto(base + authorEdit);
        assert.equal(await page.locator('main img').getAttribute('src'), oldPhoto);
        await page.locator('#name').fill('Edited browser author');
        await page.locator('#country').fill('Morocco');
        await page.locator('#photo').setInputFiles(photo);
        await page.getByRole('button', { name: 'Save author' }).click();
        await page.waitForURL(`${base}/authors/`);
        assert.equal((await context.request.get(base + oldPhoto)).status(), 404);
        authorRow = page.getByRole('row').filter({ hasText: 'Edited browser author' });
        assert.ok(await authorRow.getByRole('cell', { name: 'Morocco', exact: true }).isVisible());
        const newPhoto = await authorRow.locator('img').getAttribute('src');
        await page.screenshot({ path: path.join(directory, 'authors-desktop-light.png'), fullPage: true });
        await page.setViewportSize({ width: 360, height: 900 });
        await page.locator('#theme-toggle').click();
        await page.screenshot({ path: path.join(directory, 'authors-mobile-dark.png'), fullPage: true });
        await page.goto(`${base}/books/add`);
        await page.locator('#title').fill('Cascade browser book');
        await page.locator('#price').fill('15.00');
        await page.locator('#author_id').selectOption(authorId);
        await page.locator('#cover').setInputFiles(photo);
        await page.getByRole('button', { name: 'Save book' }).click();
        await page.waitForURL(`${base}/books/`);
        const cascadeRow = page.getByRole('row').filter({ hasText: 'Cascade browser book' });
        const cascadeCover = await cascadeRow.locator('img').getAttribute('src');
        await page.goto(`${base}/authors/`);
        await authorRow.getByRole('link', { name: 'Delete', exact: true }).click();
        await page.getByRole('button', { name: 'Delete author and books', exact: true }).click();
        await page.waitForURL(`${base}/authors/`);
        assert.equal(await authorRow.count(), 0);
        assert.equal((await context.request.get(base + newPhoto)).status(), 404);
        assert.equal((await context.request.get(base + cascadeCover)).status(), 404);
        await page.goto(`${base}/books/`);
        assert.equal(await cascadeRow.count(), 0);

        const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 360, height: 900 } });
        const fallback = await noJS.newPage();
        await fallback.goto(`${base}/_books_test/login`);
        await fallback.goto(`${base}/authors/add`);
        await fallback.locator('#name').fill('No JavaScript author');
        await fallback.locator('#country').fill('Egypt');
        await fallback.getByRole('button', { name: 'Save author' }).click();
        await fallback.waitForURL(`${base}/authors/`);
        assert.ok(await fallback.getByRole('cell', { name: 'No JavaScript author', exact: true }).isVisible());
        await fallback.goto(`${base}/books/add`);
        await fallback.locator('#title').fill('No JavaScript book');
        await fallback.locator('#price').fill('0');
        await fallback.locator('#author_id').selectOption('2');
        await fallback.getByRole('button', { name: 'Save book' }).click();
        await fallback.waitForURL(`${base}/books/`);
        assert.ok(await fallback.getByRole('cell', { name: 'No JavaScript book', exact: true }).isVisible());
        await noJS.close();
        assert.deepEqual(errors, []);
        console.log('PASS: books/authors desktop/360px, both themes, CRUD, cover/photo retention/replacement, author cascade/file cleanup, and no-JavaScript forms. Production media endpoint verified.');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exit(1); });
