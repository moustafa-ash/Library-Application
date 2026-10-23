# Library application — Lab 3

Flask/Jinja, MySQL, PyMySQL, plain CSS, and minimal JavaScript.

## Current status

Shared setup includes the app factory, configuration, database helper,
registration/login/logout, CSRF protection, server-side sessions, and the
Lab 2 light/dark design. Books/authors modules and Problem 2 SQL remain empty.
The signed-in home is a welcome screen until those modules are implemented.

## Implementation documents

Read [the library and image-bonus plan](docs/plan.md),
[team ownership](docs/work_split.md), and
[the implementation checklist](docs/checklist.md). The bonus is planned;
uploads and the Pillow dependency have not been implemented or installed yet.

## Run locally

1. Create a virtual environment from the repository root (Python 3.12 or newer):

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r website/requirements.txt
   ```

2. Prepare `website/.env`. If it does not exist, copy `website/.env.example`.
   Set your MySQL credentials and a random `SECRET_KEY`. Existing local values
   must be kept private. `DB_NAME=library` is the future catalog database;
   `AUTH_DB_NAME=registration` reuses Lab 2 accounts on the same MySQL server.
   Environment variables override `.env`. No file depends on the launch folder.

3. Start MySQL. Existing Lab 2 users work without migration. On a new instance,
   execute `website/database/auth.sql` in DBeaver to create `registration.users`.
   This optional script does not drop databases or create to-do tables.
   `problem2_DDL.sql` is still empty, so the library database is not created yet.

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
   runs `SELECT 1`, checking authentication first and then the library. Until
   the library SQL is implemented and executed, its connection check will fail.

## Team ownership

| Area | Moustafa | Ibrahim |
| --- | --- | --- |
| Feature | Books routes, queries, templates, tests | Authors routes, queries, templates, tests |
| Shared work | Flask setup, config, connection | Authentication, shared layout, theme |
| Library SQL | BOOK and at least six book seeds | AUTHOR and at least three author seeds |

The shared `get_connection()` helper selects `DB_NAME` by default; pass
`current_app.config["AUTH_DB_NAME"]` for authentication. Always use context
managers, parameterized SQL, and explicit commits for writes. Future feature
Blueprints should export `books` / `authors`, with `index` endpoints, and use
`login_required` on every route. Register them in `create_app` when implemented.
The catalog is shared; it has no per-user ownership column.

## Automatic tests and audit

[Setup tests](.github/workflows/tests.yml) runs on pull requests to `main` and
pushes to `init-setup`/`main`. It installs the pinned Python requirements, checks
dependencies, runs the unit and real MySQL tests in an isolated MySQL 8.4
service, and checks the shared pages with Chrome at desktop/mobile sizes.
It needs no private `.env` or repository secrets. The browser test tool is
installed only on the CI runner; it is not a Python application dependency.

The normal local unittest command skips the two opt-in MySQL tests. To include
them, set `RUN_MYSQL_TESTS=1`, `MYSQL_TEST_USER`, and `MYSQL_TEST_PASSWORD`;
optionally set `MYSQL_TEST_HOST` and `MYSQL_TEST_PORT`. The account must be able
to create/drop uniquely generated `library_setup_test_*` databases. Scripts are
rewritten to those database names; existing application databases are preserved.
The tests create their own users and never use real account passwords.

To run `python website/tests/browser.py` locally, provide Node.js, Chrome, and
an existing Playwright installation through `NODE_PATH`. It starts and stops a
temporary server and uses temporary session files without connecting to MySQL.
Read [the setup and plan audit](docs/audit.md) for findings, evidence, and limits.

## Problem 1

`problem1_DDL.sql` defines COMPANY and `problem1_DML.sql` inserts three rows in
each table. **The DDL drops and recreates `company`; executing it destroys any
existing data in that database.** Run DDL before DML only when that reset is
intended. `problem1_Answers.txt` is still an empty placeholder.

Private `.env`, local sessions, `AGENTS.md`, and `design.md` are Git-ignored.
Do not copy environment files or session storage from Lab 2.
