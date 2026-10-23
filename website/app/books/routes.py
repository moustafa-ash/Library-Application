from decimal import Decimal, InvalidOperation

import pymysql
from flask import abort, current_app, flash, redirect, render_template, request, url_for

from . import books, queries
from ..auth import login_required
from ..db import get_connection
from ..images import delete_image, save_image


def _render(template, **context):
    return render_template("books/" + template, media_available="media.image" in current_app.view_functions,
                           **context)


def _unavailable():
    current_app.logger.exception("Books database unavailable")
    return render_template("error.html", code=503, heading="Books are unavailable",
        message="Check the library connection and complete the AUTHOR and BOOK database setup."), 503


def _cleanup(filename):
    if filename:
        try:
            delete_image(filename, "books")
        except (OSError, ValueError):
            current_app.logger.exception("Book cover cleanup failed")


def _validate():
    title = request.form.get("title", "").strip()
    errors = []
    if not title or len(title) > 255:
        errors.append("Title is required and must be at most 255 characters.")
    price = None
    try:
        price = Decimal(request.form.get("price", ""))
        if (not price.is_finite() or price < 0 or price > Decimal("99999999.99")
                or price.as_tuple().exponent < -2):
            raise ValueError
    except (InvalidOperation, ValueError):
        errors.append("Price must be between 0 and 99999999.99, with at most two decimal places.")
    try:
        author_id = int(request.form.get("author_id", ""))
        if not 1 <= author_id <= 2147483647:
            raise ValueError
    except ValueError:
        author_id = None
        errors.append("Choose an existing author.")
    return title, price, author_id, errors


@books.get("/")
@login_required
def index():
    try:
        with get_connection() as connection:
            records = queries.list_books(connection)
    except pymysql.MySQLError:
        return _unavailable()
    return _render("index.html", books=records)


@books.route("/add", methods=["GET", "POST"])
@books.route("/<int:book_id>/edit", methods=["GET", "POST"])
@login_required
def form(book_id=None):
    book = None
    errors = []
    new_filename = None
    old_filename = None
    try:
        with get_connection() as connection:
            if book_id is not None:
                book = queries.get_book(connection, book_id, lock=request.method == "POST")
                if book is None:
                    abort(404)
            authors = queries.list_authors(connection)
            try:
                if request.method == "POST":
                    title, price, author_id, errors = _validate()
                    if author_id is not None and not queries.author_exists(connection, author_id):
                        errors.append("Choose an existing author.")
                    if not errors:
                        old_filename = book["cover_filename"] if book else None
                        cover = request.files.get("cover")
                        if cover and cover.filename:
                            # shortcut: files and MySQL are not atomic; reconcile orphans after a crash.
                            new_filename = save_image(cover, "books")
                        filename = new_filename or old_filename
                        if book is None:
                            queries.insert_book(connection, title, price, author_id, filename)
                        else:
                            queries.update_book(connection, book_id, title, price, author_id, filename)
                        connection.commit()
                    else:
                        connection.rollback()
            except (pymysql.MySQLError, OSError, ValueError) as error:
                try:
                    connection.rollback()
                finally:
                    _cleanup(new_filename)
                    new_filename = None
                if isinstance(error, ValueError):
                    errors.append(str(error))
                else:
                    current_app.logger.exception("Book save failed")
                    errors.append("Unable to save the book. Check the author and try again.")
    except pymysql.MySQLError:
        return _unavailable()

    if request.method == "POST" and not errors:
        if new_filename:
            _cleanup(old_filename)
        flash("Book saved.", "success")
        return redirect(url_for("books.index"))
    return _render("form.html", book=book, authors=authors, errors=errors)


@books.route("/<int:book_id>/delete", methods=["GET", "POST"])
@login_required
def delete(book_id):
    errors = []
    try:
        with get_connection() as connection:
            book = queries.get_book(connection, book_id, lock=request.method == "POST")
            if book is None:
                abort(404)
            if request.method == "POST":
                try:
                    queries.delete_book(connection, book_id)
                    connection.commit()
                except pymysql.MySQLError:
                    connection.rollback()
                    current_app.logger.exception("Book deletion failed")
                    errors.append("Unable to delete the book. Please try again.")
    except pymysql.MySQLError:
        return _unavailable()
    if request.method == "POST" and not errors:
        _cleanup(book["cover_filename"])
        flash("Book deleted.", "success")
        return redirect(url_for("books.index"))
    return _render("delete.html", book=book, errors=errors)
