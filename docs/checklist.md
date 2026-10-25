# Implementation and evidence checklist

Use [plan.md](plan.md) for behavior and [work_split.md](work_split.md) for owners.
Evidence below was refreshed on 2026-10-24 after implementing Ibrahim's author
feature and media integration. Items requiring live MySQL/browser evidence remain unchecked.

## Existing shared setup

- [x] Modular Flask foundation and separate registration/library database settings exist.
- [x] Login/register/logout, password hashing, CSRF, and server-side sessions exist.
- [x] Local `.venv` and pinned requirements are installed; Git ignores `.venv`, `.env`, and instance data.
- [x] Shared light/dark authentication pages and recovery templates exist.
- [x] Shared tests exist; the previous setup verification recorded 10 passing tests and desktop/360px browser checks.

## Required Part II before bonus

- [x] Implement AUTHOR/BOOK DDL, required author country, and the cascade foreign key.
- [x] Insert at least three authors and six books in the run-once seed script.
- [x] Complete authenticated books/authors tables and add/edit/delete flows, including visible book `author_id`.
- [ ] Verify validation, nonexistent records, CSRF, authentication, and no-JavaScript forms.
- [x] Register both feature Blueprints and add navigation/home routing.

## Shared image foundation

- [x] Pin Pillow and create the shared image helper.
- [x] Implement actual-format checks, 5 MiB/file, 6 MiB/request, 20,000,000 pixels, and rejection of corrupt/animated/unsupported uploads.
- [x] Normalize to metadata-free RGB JPEG, at most 1600 x 1600px, using generated filenames under the ignored upload root.
- [x] Add authenticated safe media serving and the 413 recovery page.
- [x] Add author upload, replacement, cascade cleanup, and media access tests.

## Moustafa: books and covers

- [x] Add nullable `cover_filename` to BOOK and retain NULL filenames in seed rows; verified on disposable MySQL.
- [x] Add optional cover inputs, current-image previews, accessible thumbnails, and readable fallbacks.
- [x] Verify create with/without cover and edit without a new file, preserving the existing cover.
- [x] Verify replacement, book deletion, invalid-author rejection, and file cleanup after failed SQL.
- [x] Record passing book/helper tests and a real MySQL cover-upload demonstration using a test-only media endpoint.

## Ibrahim: authors and photos

- [x] Add required AUTHOR.country and nullable `photo_filename`; seed all three authors with countries.
- [x] Add optional photo inputs, current-image previews, accessible thumbnails, and readable fallbacks.
- [x] Add author CRUD routes, parameterized queries, validation, and feature tests.
- [x] Run author/media unit tests for create/update/delete, image lifecycle, CSRF, protected media, and request-size recovery.
- [x] Add a disposable-MySQL test for author deletion, photo/cover cleanup, and preservation of another author’s data/files.

## Shared media integration

- [x] Register protected `/media/<kind>/<filename>` serving with strict generated-name checks and `nosniff`.
- [x] Apply the 6 MiB request limit and render a recovery page for oversized requests.
- [x] Add shared responsive table and author image styles; expose authors from home navigation.
- [ ] Verify protected media and database cascade/file cleanup against disposable MySQL and in the browser.

## Joint acceptance and handoff

- [x] Run the full discovered suite and `pip check` after author/media integration.
- [x] Run the real author-delete MySQL integration test against disposable rows/database and temporary uploads in CI; assert unrelated data/files are preserved.
- [ ] Check desktop and 360px mobile, both themes, keyboard use, table scrolling, errors, missing images, and no-JavaScript forms.
- [x] Update README with setup, upload limits, local storage/backup, new-database scripts, and demo steps; keep credentials/uploads out of Git.
- [x] Record current unit test, dependency, and local SQL evidence; leave live cascade/browser items unchecked.

## Evidence log

| Check | Result | Evidence |
| --- | --- | --- |
| Books SQL and CRUD | Previously passed on disposable MySQL | Historical evidence from before author integration; `test_books_mysql.py` now consumes the combined AUTHOR/BOOK scripts. |
| Unit regression suite | Passed | `python -m unittest discover -s website/tests -t website`: 41 tests, 5 opt-in MySQL tests skipped. Author/media tests passed. |
| Dependencies | Passed | `pip check`: no broken requirements. |
| Local database and app | Passed by user | Workbench output showed three authors and six books inserted; user reported the local app runs. |
| MySQL cascade and file cleanup | Passed in CI | Disposable-MySQL test posts to the real author-delete route, removes one photo/two covers, and preserves another author and their files. |
| Book desktop/mobile review | Previously passed with fixtures | Historical fixture browser checks; author pages and production media have not received browser review. |
| Cover demo evidence | Fixture demo passed | Visually inspected `website/instance/book-checks/mobile-dark-edit.png` and `desktop-light-edit.png`; real MySQL with test-only login/media routes. |
| Shared upload integration | Implemented; unit tests passed | Helper, author/media, request-limit, and book preview tests passed. Real MySQL cascade/file cleanup remains unverified. |
| CI | Passed on PR | Disposable MySQL tests and desktop/mobile browser checks passed on GitHub Actions. |

## Handoff / remaining prerequisites

1. Run real author-cascade cleanup against a disposable database and review the
   author pages in the browser at desktop/mobile sizes.
2. The image helper is ready for both kinds. Upload root defaults to the
   instance uploads directory; `UPLOAD_ROOT` can override it for tests/config.
3. README contains setup, test commands, books/authors demo, image limits/storage,
   backup/reconciliation notes. Joint final demo remains unchecked.
4. Problem 1 files, Lab 2 data, private `.env`, and Ibrahim's feature files were
   preserved. The PDF's individual-work wording and the two-person project plan
   remain a recorded mismatch; no instructor approval is asserted.
