# Library application and image bonus plan

**Status:** planning only; this document does not authorize implementation.

**Goal:** finish Part II's books/authors CRUD, then support optional book covers
and author photos without changing the existing authentication system.

**Architecture:** Flask feature Blueprints, Jinja forms, parameterized PyMySQL
queries, and one shared local image helper. Keep the library at two tables;
store image filenames in those tables and image bytes outside the static folder.

**Sources:** LAB3.pdf, Part II (pages 2-3); the current repository and
[README](../README.md). The PDF requests covers and photos but does not specify
formats, sizes, storage, or replacement rules. The defaults below are project
decisions, not additional assignment requirements.

## 1. Starting point and sequence

1. Shared Flask configuration, authentication, CSRF, server-side sessions, and
   light/dark pages are implemented. The project has a local `.venv` and pinned
   `website/requirements.txt`. Existing tests cover shared setup, not uploads.
2. Implement `problem2_DDL.sql` and `problem2_DML.sql`, with AUTHOR before BOOK,
   `BOOK.author_id -> AUTHOR.author_id ON DELETE CASCADE`, and at least three
   authors and six books. The library database has not yet been created in this
   project. Keep `registration.users` separate.
3. Finish both required CRUD modules and their tests before bonus integration.
   Show the assignment's fields, including book `author_id`; protect every route
   with `login_required` and every write with the existing CSRF check.
4. Implement the shared image helper, configuration, and protected media route;
   then integrate covers and photos in their respective feature forms.
5. Verify upload lifecycle and cascade cleanup together; update the run guide
   and record real demo evidence. Do not submit, publish, or reset databases as
   part of implementing this plan.

## 2. Storage, interfaces, and dependencies

| Area | Decision |
| --- | --- |
| Schema | Add nullable `BOOK.cover_filename VARCHAR(36)` and `AUTHOR.photo_filename VARCHAR(36)`. Keep all required fields and only two library tables. Seed filenames are NULL. |
| Files | `website/instance/uploads/books/` and `website/instance/uploads/authors/`; both are already covered by the instance-directory Git exclusion. Store only a generated basename in MySQL. |
| Filenames | `uuid4().hex + '.jpg'` (36 characters). Never use the submitted filename or accept a filesystem path from a form. |
| Shared helper | Create `website/app/images.py`: `save_image(upload, kind) -> filename` and `delete_image(filename, kind) -> None`; allow only `kind='books'` or `'authors'`. Invalid images raise `ValueError`; storage failures raise `OSError`. Deletion validates the generated basename and never escapes the selected directory. |
| Serving | Register `GET /media/<kind>/<filename>` as endpoint `media.image`, with `login_required`, strict kind/basename checks, and Flask `send_from_directory` rooted in the selected upload directory. Return 404 for invalid/missing files; serve JPEG with `X-Content-Type-Options: nosniff`. |

Create `website/app/media.py` for the media Blueprint; wire it into the app
factory. Extend existing feature queries and templates rather than adding
controllers, an ORM, storage services, or another database table.

Add Pillow to the project `.venv` at implementation time, after dependency
approval, and pin the tested compatible version in the existing requirements
file. Pillow is planned, not currently installed for this bonus. No cloud
storage, external image service, cropping editor, gallery, or image-removal
control is required. Users can replace an image or delete its record.

The image columns are an optional schema extension for the bonus. Because the
library DDL is still empty, include them in its first implementation. If a
teammate has already populated a library database by then, use reviewed additive
ALTER statements that preserve rows; do not reset it to add these columns.

## 3. Upload rules and user experience

1. Add one optional `cover` file input to book add/edit forms and one optional
   `photo` input to author add/edit forms. Use `multipart/form-data`, the existing
   hidden CSRF token, visible labels, and ordinary Save/Cancel actions. A form
   works without JavaScript. On edit, no selection retains the current image.
2. Accept `.jpg`, `.jpeg`, `.png`, and `.webp`, matching the actual decoded
   image format. Reject empty/corrupt files, animated images, SVG, GIF, and
   mismatched extensions. Do not trust browser MIME type or `accept` alone.
3. Limit each image to 5 MiB (5,242,880 bytes) and the complete request to 6 MiB
   through `MAX_CONTENT_LENGTH`. Limit decoded images to 20,000,000 pixels;
   treat Pillow decompression-bomb warnings/errors as rejection as well. Fully
   decode the image; checking a filename or header alone is insufficient.
4. Apply EXIF orientation, fit within 1600 x 1600 pixels without stretching or
   upscaling, composite transparency on white, and save a fresh RGB JPEG at
   quality 85 without copying EXIF or other metadata. Write to a temporary file
   in the target folder, then atomically rename it to the generated basename.
5. Show a 48 x 64px contained cover or 48 x 48px contained photo beside the
   required table fields, plus a larger preview on edit. Use descriptive alt
   text; use readable "No cover" / "No photo" fallbacks. Errors preserve text
   fields and explain that a file must be selected again. A 413 recovery page
   explains the size limit. Retain both themes and mobile table scrolling.

## 4. Database and file lifecycle

| Operation | Required order and failure behavior |
| --- | --- |
| Create | Validate text/relationships, validate and save the optional image, then INSERT its filename and commit. On SQL failure, roll back and delete the newly saved file. On image failure, do not create a record. |
| Edit without upload | Update text fields while retaining the current filename. Never replace it with an empty value just because the browser submitted no file. |
| Replace image | Within the record's write transaction, lock/read the current row, save a new generated file, and UPDATE its filename. On rollback, delete the new file and retain the old one. Only after commit remove the old file. |
| Delete book | Lock/read its row and filename, DELETE, commit, then remove the cover. A failed SQL deletion keeps the record and image. |
| Delete author | Lock/read the author and affected books, collect their photo/cover filenames, then DELETE the author and commit. MySQL cascades BOOK rows only; application code must then remove the photo and all collected covers. |

Feature query helpers must accept the caller's connection for these multi-step
operations, so reading filenames and writing/deleting rows share one transaction.
Keep entity SQL in each feature's `queries.py` and file handling in `images.py`.
On unknown record IDs, return 404 without saving an image. An invalid book
author must not leave a new file behind, including a foreign-key race.

File deletion after a successful database commit is best effort: tolerate an
already-missing file, log other cleanup errors, and keep the successful record
change. Never undo a committed deletion by inventing replacement rows. A broken
image request must fall back to the readable no-image state.

**Known limit:** MySQL and local files do not share an atomic transaction. A
process crash between saving a file and committing SQL, or a cleanup failure,
can leave an unreferenced file. Accept this bounded local-demo limit, document
manual reconciliation, and add no background worker or cleanup service now.
Back up the database and upload directory together if preserving the demo.

## 5. Verification and completion

1. Add `website/tests/test_images.py` with small generated image fixtures and a
   temporary upload root. Prove format/size/pixel/animation checks, normalized
   filenames, conversion, and traversal rejection. Write failing cases before
   implementing the helper.
2. Extend each entity's tests for create without/with image, edit without new
   image, replacement, bad upload, missing record, invalid author, SQL rollback,
   and disk failure. Assert retained/deleted files as well as database behavior.
3. Test the media route with and without authentication, missing files, invalid
   kinds, traversal attempts, JPEG headers, and CSRF rejection of upload POSTs.
   Verify oversized requests use the shared 413 recovery page.
4. Use a disposable MySQL database and temporary uploads for the real cascade
   test: delete one author with at least two covered books; retain a different
   author's records/files. Mocked database tests cannot prove MySQL cascading.
5. Run the existing suite, dependency checks, and desktop/360px browser checks in
   light/dark themes. Demonstrate at least one uploaded cover and one photo,
   replacement, and author cascade cleanup. Mark only observed results complete
   in [checklist.md](checklist.md); use [work_split.md](work_split.md) for ownership.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s website/tests -t website
```

Implementation references: [Flask file uploads](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/)
for multipart requests, request limits, and safe serving;
[Pillow Image API](https://pillow.readthedocs.io/en/stable/reference/Image.html)
for decoding and decompression limits. The numerical limits and JPEG
normalization above are deliberate project defaults.
