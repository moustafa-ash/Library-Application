# Library application — Lab 3

Flask/Jinja, MySQL, PyMySQL, plain CSS, and minimal JavaScript.

## Current status

Shared setup includes the app factory, configuration, database helper,
registration/login/logout, CSRF protection, server-side sessions, and the Lab 2
light/dark design. Authenticated books and authors CRUD, cover/photo lifecycles,
AUTHOR/BOOK SQL and sample seeds, protected media serving, and upload recovery
are implemented. Check `docs/checklist.md` for verification still requiring a
disposable MySQL/browser demonstration.

On 2026-10-24, `problem2_DDL.sql` and `problem2_DML.sql` were run in MySQL
Workbench. The output showed three authors and six books in `library`; the app
was started locally. Real disposable-MySQL author-cascade cleanup and browser
checks for the new author/media pages still need to be run.

## Implementation documents

Read [the library and image-bonus plan](docs/plan.md),
[team ownership](docs/work_split.md), and
[the implementation checklist](docs/checklist.md). Pillow 13.0.0 is pinned and
the shared image helper is implemented. The plan describes joint behavior;
the checklist records completed implementation and remaining verification.

## Run locally

1. Create a virtual environment from the repository root (Python 3.12 or newer):

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r website/requirements.txt
   ```

2. Prepare `website/.env`. If it does not exist, copy `website/.env.example`.
   Set your MySQL credentials and a random `SECRET_KEY`. Existing local values
   must be kept private. `DB_NAME=library` is the catalog database;
   `AUTH_DB_NAME=registration` reuses Lab 2 accounts on the same MySQL server.
   Environment variables override `.env`. No file depends on the launch folder.

3. Start MySQL. Existing Lab 2 users work without migration. On a new instance,
   execute `website/database/auth.sql` in DBeaver to create `registration.users`.
   This optional script does not drop databases or create to-do tables.
   For a new catalog, create `library`, then run `problem2_DDL.sql` and
   `problem2_DML.sql` once. The schema includes required author name/country
   fields and the BOOK cascade foreign key; the seed script inserts three authors
   before six illustrative books. These scripts are not resets or migrations.
   For an existing catalog made before AUTHOR.country was added, run
   `website/database/add_author_country.sql` once. It preserves rows and fills
   the new required field with `Unknown`; update those countries in **Browse
   authors**. Do not rerun the migration.

4. Start the local application from the repository root:

   ```powershell
   .\.venv\Scripts\python.exe -m flask --app website/run.py run
   ```

   Open <http://127.0.0.1:5000>. Register or log in with an existing Lab 2
   account. Debug mode is off by default. For HTTPS deployment, set
   `SESSION_COOKIE_SECURE=true`; leave it false for local HTTP development.

5. Run tests and check database connections:

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s website/tests -t website
   .\.venv\Scripts\python.exe -m flask --app website/run.py check-db
   ```

   Unit tests mock MySQL and use temporary session storage. `check-db` only
   runs `SELECT 1`, checking authentication first and then the library. It does
   not verify that AUTHOR or BOOK exists. Book integration tests below use
   real MySQL and disposable fixtures instead of mocking the database.

## Team ownership

| Area | Moustafa | Ibrahim |
| --- | --- | --- |
| Feature | Books routes, queries, templates, tests | Authors routes, queries, templates, tests |
| Shared work | Flask setup, config, connection | Authentication, shared layout, theme, media, upload handling |
| Library SQL | BOOK and at least six book seeds | AUTHOR and at least three author seeds |

The shared `get_connection()` helper selects `DB_NAME` by default; pass
`current_app.config["AUTH_DB_NAME"]` for authentication. Always use context
managers, parameterized SQL, and explicit commits for writes. Feature Blueprints
export `books` / `authors` and protect every route with `login_required`.
The catalog is shared; it has no per-user ownership column.

## Automatic tests and audit

[Setup tests](.github/workflows/tests.yml) runs on pull requests to `main` and
pushes to `init-setup`/`main`. It installs the pinned Python requirements, checks
dependencies, runs the unit and real MySQL tests in an isolated MySQL 8.4
service, and checks the shared pages with Chrome at desktop/mobile sizes.
It needs no private `.env` or repository secrets. The browser test tool is
installed only on the CI runner; it is not a Python application dependency.

The normal local unittest command skips six opt-in MySQL tests (two setup,
three book checks and one author-delete integration check). To include the original setup tests, set `RUN_MYSQL_TESTS=1`,
`MYSQL_TEST_USER`, and `MYSQL_TEST_PASSWORD`;
optionally set `MYSQL_TEST_HOST` and `MYSQL_TEST_PORT`. The account must be able
to create/drop uniquely generated `library_setup_test_*` databases. Scripts are
rewritten to those database names; existing application databases are preserved.
The tests create their own users and never use real account passwords.

To run `python website/tests/browser.py` locally, provide Node.js, Chrome, and
an existing Playwright installation through `NODE_PATH`. It starts and stops a
temporary server and uses temporary session files without connecting to MySQL.
Read [the setup and plan audit](docs/audit.md) for findings, evidence, and limits.

### Book verification and demonstration

1. Run book MySQL checks using the existing private connection settings:

   ```powershell
   $env:RUN_BOOK_MYSQL_TESTS='1'
   .\.venv\Scripts\python.exe -m unittest discover -s website/tests -t website
   .\.venv\Scripts\python.exe -m pip check
   ```

   Only generated `library_books_test_<uuid>` databases are created/dropped.
   The account needs CREATE/DROP DATABASE privileges. Optional `MYSQL_TEST_HOST`,
   `MYSQL_TEST_PORT`, `MYSQL_TEST_USER`, and `MYSQL_TEST_PASSWORD` override the
   connection for tests. Never put private settings in a committed command/file.
   This command does not enable the separate company tests.

2. With Chrome and an existing Playwright installation available via `NODE_PATH`,
   run `.\.venv\Scripts\python.exe website/tests/browser_books.py` with the
   same opt-in flag. This starts/stops a local fixture server and verifies book
   pages in both themes at 1366px/360px, upload/retention/delete, and a no-JavaScript
   create. Its login/media endpoints exist only in the fixture server.
   Screenshots are saved under ignored `website/instance/book-checks/`.

3. After database setup, log in and use **Browse books** and **Browse authors**.
   Exercise create/edit/delete for both, retain images on edits without uploads,
   replace images, and confirm author deletion removes its books and their covers.
   The seeded book titles are illustrative fixtures; coordinate final catalog content.

### Image helper handoff

`app.images.save_image(upload, kind)` returns a generated 36-character JPEG
basename; `delete_image(filename, kind)` removes it and tolerates missing files.
Kinds are exactly `books` and `authors`. Invalid content/kinds/names raise
`ValueError`; disk failures raise `OSError`. The default root is
`website/instance/uploads/`; tests can set `UPLOAD_ROOT` to a temporary directory.
Never pass a browser-supplied path into storage or serving.

JPG/JPEG, PNG, and WebP must match their decoded format. The helper rejects
empty/corrupt/animated images, files over 5 MiB, images over 20 million pixels,
and decompression-bomb warnings/errors. It applies EXIF orientation, fits within
1600 x 1600 without upscaling, composites transparency onto white, and atomically
stores a fresh RGB JPEG at quality 85 without copied metadata.

The protected `media.image` endpoint serves generated JPEG basenames at
`/media/<kind>/<filename>` with strict validation and nosniff headers.
`MAX_CONTENT_LENGTH=6 * 1024 * 1024` and a 413 recovery page complement the
5 MiB per-file helper limit. Author deletion removes affected covers after the
database cascade commits. Shared table and author-photo styles use both themes.

Book routes lock current records on writes, commit SQL before deleting old
covers, and remove new files on rollback. Post-commit cleanup is best effort
and logs failures. MySQL/filesystem operations are not one atomic transaction:
a crash, ambiguous connection loss during commit, or cleanup failure can leave
orphaned/missing files. Back up database/uploads together. For reconciliation,
compare stored BOOK.cover_filename and AUTHOR.photo_filename values with the
two upload folders, review differences, and only then remove confirmed orphans.
No automatic cleanup worker is included.

Local verification on 2026-10-23: 32 tests passed, two original setup MySQL tests
were skipped; four book/author MySQL tests actually ran. Dependency checks and book
desktop/mobile browser checks passed, including keyboard focus and missing-image
fallback; the original shared browser checks passed too. CI opts into book MySQL/browser
checks too; hosted CI has not been run in this session.

## Problem 1

`problem1_DDL.sql` defines COMPANY and `problem1_DML.sql` inserts three rows in
each table. **The DDL drops and recreates `company`; executing it destroys any
existing data in that database.** Run DDL before DML only when that reset is
intended. `problem1_Answers.txt` contains the separate exercise answers;
Problem 1 files were preserved during the books implementation.

Private `.env`, local sessions, `AGENTS.md`, and `design.md` are Git-ignored.
Do not copy environment files or session storage from Lab 2.
