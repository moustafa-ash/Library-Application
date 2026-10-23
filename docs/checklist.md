# Implementation and evidence checklist

Use [plan.md](plan.md) for behavior and [work_split.md](work_split.md) for owners.
Checked items below are prior completed setup reported in this session and
confirmed by the current files. They are not fresh test results from this
documentation-only update. Every unchecked item is future work.

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

- [ ] Approve/install Pillow and update the existing requirements; create and test the one shared image helper.
- [ ] Enforce actual-format checks, 5 MiB/file, 6 MiB/request, 20,000,000 pixels, and rejection of corrupt/animated/unsupported uploads.
- [ ] Normalize to metadata-free RGB JPEG, at most 1600 x 1600px, using generated filenames under the ignored upload root.
- [ ] Add authenticated safe media serving and the 413 recovery page; verify traversal and unauthenticated-access rejection.
- [ ] Verify missing files, disk errors, SQL rollback, and retained existing images on failed replacements.

## Moustafa: books and covers

- [ ] Add nullable `cover_filename` to BOOK and retain NULL filenames in seed rows.
- [ ] Add optional cover inputs, current-image previews, accessible thumbnails, and readable fallbacks.
- [ ] Verify create with/without cover and edit without a new file, preserving the existing cover.
- [ ] Verify replacement, book deletion, invalid-author rejection, and file cleanup after failed SQL.
- [ ] Record passing book/helper tests and one real cover-upload demonstration.

## Ibrahim: authors and photos

- [ ] Add nullable `photo_filename` to AUTHOR and retain NULL filenames in seed rows.
- [ ] Add optional photo inputs, current-image previews, accessible thumbnails, and readable fallbacks.
- [ ] Verify create with/without photo, edit without a new file, and replacement.
- [ ] Verify author-delete confirmation, cascaded book deletion, and cleanup of the photo plus every affected cover.
- [ ] Record passing author/media tests and one real photo-upload/cascade demonstration.

## Joint acceptance and handoff

- [ ] Run the full unit suite and `pip check` in the project `.venv`; record results below.
- [ ] Run the real MySQL cascade test using disposable rows/database and temporary uploads; prove unrelated data is preserved.
- [ ] Check desktop and 360px mobile, both themes, keyboard use, table scrolling, errors, missing images, and no-JavaScript forms.
- [ ] Update README with setup, upload limits, local storage/backup, new-database scripts, and demo steps; keep credentials/uploads out of Git.
- [ ] Record evidence for each bonus operation; leave incomplete or failed checks visibly unchecked.

## Evidence log

| Check | Result | Evidence |
| --- | --- | --- |
| Core library CRUD | Not implemented | Feature modules and Problem 2 SQL are empty at planning time. |
| Bonus unit/integration tests | Not implemented | No upload helper, media route, or bonus tests exist yet. |
| MySQL cascade and file cleanup | Not run | Requires core tables plus the upload implementation. |
| Bonus desktop/mobile review | Not run | No bonus UI has been implemented. |
| Final demo | Not run | Add real screenshots/test output after implementation. |
