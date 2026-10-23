# Setup and plan audit - 23 October 2026

**What this repo does:** it provides a local Flask authentication foundation,
Problem 1 COMPANY SQL, and empty modules plus a plan for the library and image
bonus. Expected load is a two-person student project on local MySQL, not a
public production service.

## Findings

No must-fix implementation defect was found in the current setup. Two
verification gaps needed attention before opening a tested pull request.

1. **Database behavior was only mocked** (`website/tests/test_auth.py`,
   `website/tests/test_setup.py`). **What this is:** existing tests simulated
   MySQL results. **Problem:** they could pass even if the actual SQL failed or
   authentication disagreed with the users table. **Fix:** added opt-in real
   MySQL tests that rewrite setup scripts to uniquely named disposable databases
   and test seed counts, both foreign-key failures, registration, hashed storage,
   login/logout, duplicate email handling, and escaped user output.
   **If skipped:** unit success would not prove MySQL integration.

2. **Pull requests had no automatic checks** (`.github/workflows/tests.yml`,
   `website/tests/browser.py`, `website/tests/browser.test.js`).
   **What this is:** checks previously ran only on this computer.
   **Problem:** a changed dependency, SQL statement, or theme script could be
   merged without a repeatable check. **Fix:** added a read-only-permission
   GitHub Actions workflow with Python 3.14, MySQL 8.4, dependency validation,
   the Python suite, and real Chrome checks. **If skipped:** the merge decision
   would depend on historical local results.

## Plan review

The plan keeps required CRUD ahead of the bonus, maintains two library tables,
and separates existing authentication data. Ownership stays books/covers for
Moustafa and authors/photos for Ibrahim. Upload validation, SQL rollback,
replacement, authenticated serving, and author-cascade file cleanup are covered.
The filename columns are documented bonus extensions, not PDF requirements.
The local-file/database crash gap is explicitly accepted for this local demo.
No additional service, framework, or schema table is needed.

## Evidence

| Check | Observed result |
| --- | --- |
| Original unit baseline | 10 tests passed; `pip check` found no conflicts. |
| Expanded suite against local MySQL | 12 tests passed, including both new real-MySQL tests. Generated test databases were removed. |
| Browser script | Desktop 1366px and mobile 360px passed in light/dark themes, with theme persistence, blocked storage, no-JavaScript forms, no horizontal overflow, and controls at least 44px tall. |
| Secrets and scope | `.env`, `.venv`, session files, and local planning instructions stay ignored. Books/authors and Problem 2 SQL remain empty. |
| Hosted workflow | See the pull request's current Setup tests check; local results alone do not establish a hosted pass. |

The audit read shared Python, SQL, templates, CSS, JavaScript, requirements,
tests, README, and all implementation-plan documents. Ibrahim's name was
corrected across project Markdown, including ignored local instructions.

**Verdict:** healthy for an initial-setup PR once its hosted checks pass. The
verification gaps are addressed without changing application behavior.

**Not checked:** future books/authors CRUD, image uploads, bonus cascade cleanup,
Problem 1 answer output, production traffic, or deployment. Empty scaffolds and
unchecked plan tasks remain unfinished deliverables; this is not a completed
assignment or authorization to merge.
