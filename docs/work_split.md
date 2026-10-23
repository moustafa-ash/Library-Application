# Work split

**Moustafa owns books and covers. Ibrahim owns authors and photos.** Each owns
their backend, queries, templates, and feature tests. The shared setup already
exists; the table below assigns the remaining core and bonus work.

## Balanced responsibilities

| Work package | Moustafa | Ibrahim |
| --- | --- | --- |
| Required feature | BOOK schema, at least six book seeds, book CRUD and author selector | AUTHOR schema, at least three author seeds, author CRUD and cascade confirmation |
| Bonus integration | Cover input, preview, filename queries, replacement and book-delete cleanup | Photo input, preview, filename queries, replacement and author/cascaded-cover cleanup |
| Shared bonus foundation | Implement `images.py`, safe storage, validation and normalization; add/test the Pillow dependency | Implement `media.py`, authenticated serving, upload config, 413 recovery, and shared image styles |
| Tests | Helper tests, books tests, invalid-author/SQL-failure file cleanup | Media/auth tests, authors tests, real cascade cleanup and unrelated-data preservation |
| Handoff | Storage/dependency setup and book demo steps | UI/media setup, photo/cascade demo steps and combined acceptance evidence |

## Handoffs in order

1. Agree on the contracts and defaults in [plan.md](plan.md). Moustafa starts
   the shared DDL with AUTHOR and BOOK definitions supplied by their owners;
   Ibrahim reviews the foreign key. Coordinate one editor for shared SQL files.
2. Ibrahim provides the author list query and author seeds before book
   integration. Moustafa can develop books using agreed test fixtures while
   author UI work proceeds independently.
3. Moustafa provides `save_image(upload, kind)` and
   `delete_image(filename, kind)` plus helper tests. Ibrahim uses that same
   helper for photos and media configuration; neither writes a second uploader.
4. Ibrahim leads shared template/CSS edits and app-factory media wiring;
   Moustafa supplies cover-specific markup needs. Coordinate edits to
   requirements and config so one teammate does not overwrite the other.
5. Review together: an author deletion must clean up covers owned by Moustafa's
   module as well as Ibrahim's photo. Run a disposable-data demonstration and
   record evidence in [checklist.md](checklist.md) before marking integration done.

## Planning estimates

| Remaining work | Moustafa | Ibrahim |
| --- | --- | --- |
| Core CRUD, SQL and feature tests | 150-210 minutes | 150-210 minutes |
| Bonus foundation, integration and tests | 120-180 minutes | 120-180 minutes |
| Joint verification and handoff | 45-60 minutes | 45-60 minutes |

These are planning ranges per person, not completed work or a deadline promise.
Target equal effort; adjust after reviewing the first working CRUD flow. The
bonus starts after required CRUD passes. Problem 1 answers are a separate
unfinished deliverable and have not been assigned by this image-bonus split.
