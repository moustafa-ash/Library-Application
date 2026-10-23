# Implementation and evidence checklist

Use [plan.md](plan.md) for behavior and [work_split.md](work_split.md) for owners.
Evidence below was refreshed on 2026-10-23 for Moustafa's implementation.
Unchecked combined items still depend on Ibrahim's work; see the evidence table
for the book-only portions that passed against disposable AUTHOR fixtures.

## Existing shared setup

- [x] Modular Flask foundation and separate registration/library database settings exist.
- [x] Login/register/logout, password hashing, CSRF, and server-side sessions exist.
- [x] Local `.venv` and pinned requirements exist; Git ignores `.venv`, `.env`, and instance data.
- [x] Shared light/dark authentication pages and recovery templates exist.
- [x] Shared tests exist; the previous setup verification recorded 10 passing tests and desktop/360px browser checks.

## Required Part II before bonus

- [ ] Implement AUTHOR/BOOK DDL and the cascade foreign key; run it on an approved local/test database.
- [ ] Insert at least three authors and six books; verify the saved seed data.
- [ ] Complete authenticated books/authors tables and add/edit/delete flows, including visible book `author_id`.
- [ ] Verify validation, nonexistent records, CSRF, authentication, and no-JavaScript forms.
- [ ] Register both feature Blueprints, add navigation/home routing, and pass core tests before bonus integration.

## Shared image foundation

- [x] Approve/install Pillow and update the existing requirements; create and test the one shared image helper.
- [ ] Enforce actual-format checks, 5 MiB/file, 6 MiB/request, 20,000,000 pixels, and rejection of corrupt/animated/unsupported uploads.
- [x] Normalize to metadata-free RGB JPEG, at most 1600 x 1600px, using generated filenames under the ignored upload root.
- [ ] Add authenticated safe media serving and the 413 recovery page; verify traversal and unauthenticated-access rejection.
- [x] Verify helper/book missing files, disk errors, SQL rollback, and retained existing images on failed replacements. Author behavior remains pending.

## Moustafa: books and covers

- [x] Add nullable `cover_filename` to BOOK and retain NULL filenames in seed rows; verified on disposable MySQL.
- [x] Add optional cover inputs, current-image previews, accessible thumbnails, and readable fallbacks; production preview awaits media endpoint.
- [x] Verify create with/without cover and edit without a new file, preserving the existing cover.
- [x] Verify replacement, book deletion, invalid-author rejection, and file cleanup after failed SQL.
- [x] Record passing book/helper tests and a real MySQL cover-upload demonstration using a test-only media endpoint.

## Ibrahim: authors and photos

- [ ] Add nullable `photo_filename` to AUTHOR and retain NULL filenames in seed rows.
- [ ] Add optional photo inputs, current-image previews, accessible thumbnails, and readable fallbacks.
- [ ] Verify create with/without photo, edit without a new file, and replacement.
- [ ] Verify author-delete confirmation, cascaded book deletion, and cleanup of the photo plus every affected cover.
- [ ] Record passing author/media tests and one real photo-upload/cascade demonstration.

## Joint acceptance and handoff

- [x] Run the full discovered suite with book MySQL enabled and `pip check`; results below distinguish skipped setup tests.
- [ ] Run the real MySQL cascade test using disposable rows/database and temporary uploads; prove unrelated data is preserved.
- [ ] Check desktop and 360px mobile, both themes, keyboard use, table scrolling, errors, missing images, and no-JavaScript forms.
- [ ] Update README with setup, upload limits, local storage/backup, new-database scripts, and demo steps; keep credentials/uploads out of Git.
- [ ] Record evidence for each bonus operation; leave incomplete or failed checks visibly unchecked.

## Evidence log

| Check | Result | Evidence |
| --- | --- | --- |
| Books SQL and CRUD | Passed on disposable MySQL | `test_books_mysql.py`: supplied BOOK scripts, six seeds, real create/edit/unchanged edit/delete, author rejection; AUTHOR is a test fixture. |
| Book/helper regression suite | Passed | With `RUN_BOOK_MYSQL_TESTS=1`: 34 discovered, 32 passed, two original setup MySQL tests skipped. `pip check`: no broken requirements. |
| Local connections | Passed | Both `check-db` SELECT checks passed. Live `library` created without resetting data; no live tables because AUTHOR work remains pending. |
| MySQL cascade and file cleanup | Partial | Real FK rejection and cascading BOOK rows verified, with four unrelated seeded books retained. Book-cover replacement/deletion cleanup passed. Author-photo/cascaded-cover cleanup remains pending. |
| Book desktop/mobile review | Passed with fixtures | Chrome at 1366px/360px, both themes, upload/retention/delete, keyboard focus, missing-image fallback, no-JavaScript create, no JS errors. Original shared browser checks passed too. Production media is not implemented. |
| Cover demo evidence | Fixture demo passed | Visually inspected `website/instance/book-checks/mobile-dark-edit.png` and `desktop-light-edit.png`; real MySQL with test-only login/media routes. |
| Shared upload integration | Pending Ibrahim | Actual file checks, 5 MiB, 20-million pixels, normalized output tested. 6 MiB request limit, 413, production serving, author photos and shared styles not implemented. |
| CI | Configured, not run remotely | Workflow enables book MySQL tests and book browser checks; local checks passed. |

## Handoff / remaining prerequisites

1. Ibrahim supplies AUTHOR DDL before BOOK and author seeds with IDs 1, 2, 3
   before the illustrative book seeds. Coordinate one editor for shared SQL.
2. The image helper is ready for both kinds. Upload root defaults to the
   instance uploads directory; `UPLOAD_ROOT` can override it for tests/config.
3. Ibrahim supplies `media.image`, request configuration/413, shared image
   styles, author UI/photos and cascade-file cleanup. Book previews detect
   endpoint registration and otherwise render an explicit integration fallback.
4. README contains setup, test commands, book demo, image limits/storage,
   backup/reconciliation notes. Joint final demo remains unchecked.
5. Problem 1 files, Lab 2 data, private `.env`, and Ibrahim's feature files were
   preserved. The PDF's individual-work wording and the two-person project plan
   remain a recorded mismatch; no instructor approval is asserted.
