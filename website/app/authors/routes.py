import pymysql
from flask import abort, current_app, flash, redirect, render_template, request, url_for

from . import authors, queries
from ..auth import login_required
from ..db import get_connection
from ..images import delete_image, save_image


def _cleanup(filename, kind):
    if filename:
        try:
            delete_image(filename, kind)
        except (OSError, ValueError):
            current_app.logger.exception("Author feature image cleanup failed")


def _unavailable():
    current_app.logger.exception("Authors database unavailable")
    return render_template("error.html", code=503, heading="Authors are unavailable",
        message="Check the library connection and complete the AUTHOR and BOOK database setup."), 503


def _render(template, **context):
    return render_template("authors/" + template,
        media_available="media.image" in current_app.view_functions, **context)


@authors.get("/")
@login_required
def index():
    try:
        with get_connection() as connection:
            records = queries.list_authors(connection)
    except pymysql.MySQLError:
        return _unavailable()
    return _render("index.html", authors=records)


@authors.route("/add", methods=["GET", "POST"])
@authors.route("/<int:author_id>/edit", methods=["GET", "POST"])
@login_required
def form(author_id=None):
    author = None
    errors = []
    new_photo = old_photo = None
    try:
        with get_connection() as connection:
            if author_id is not None:
                author = queries.get_author(connection, author_id, lock=request.method == "POST")
                if author is None:
                    abort(404)
            if request.method == "POST":
                name = request.form.get("name", "").strip()
                if not name or len(name) > 100:
                    errors.append("Name is required and must be at most 100 characters.")
                if not errors:
                    old_photo = author["photo_filename"] if author else None
                    upload = request.files.get("photo")
                    if upload and upload.filename:
                        new_photo = save_image(upload, "authors")
                    filename = new_photo or old_photo
                    try:
                        if author is None:
                            queries.insert_author(connection, name, filename)
                        else:
                            queries.update_author(connection, author_id, name, filename)
                        connection.commit()
                    except pymysql.MySQLError:
                        connection.rollback()
                        _cleanup(new_photo, "authors")
                        new_photo = None
                        current_app.logger.exception("Author save failed")
                        errors.append("Unable to save the author. Please try again.")
                else:
                    connection.rollback()
    except pymysql.MySQLError:
        _cleanup(new_photo, "authors")
        return _unavailable()
    except (OSError, ValueError) as error:
        _cleanup(new_photo, "authors")
        new_photo = None
        errors.append(str(error) if isinstance(error, ValueError) else "Unable to store the photo. Please try again.")

    if request.method == "POST" and not errors:
        if new_photo:
            _cleanup(old_photo, "authors")
        flash("Author saved.", "success")
        return redirect(url_for("authors.index"))
    return _render("form.html", author=author, errors=errors)


@authors.route("/<int:author_id>/delete", methods=["GET", "POST"])
@login_required
def delete(author_id):
    errors = []
    photo = None
    covers = []
    try:
        with get_connection() as connection:
            author = queries.get_author(connection, author_id, lock=request.method == "POST")
            if author is None:
                abort(404)
            if request.method == "POST":
                photo = author["photo_filename"]
                try:
                    books = queries.list_author_books(connection, author_id, lock=True)
                    covers = [book["cover_filename"] for book in books if book["cover_filename"]]
                    queries.delete_author(connection, author_id)
                    connection.commit()
                except pymysql.MySQLError:
                    connection.rollback()
                    current_app.logger.exception("Author deletion failed")
                    errors.append("Unable to delete the author. Please try again.")
    except pymysql.MySQLError:
        return _unavailable()
    if request.method == "POST" and not errors:
        _cleanup(photo, "authors")
        for filename in covers:
            _cleanup(filename, "books")
        flash("Author and related books deleted.", "success")
        return redirect(url_for("authors.index"))
    return _render("delete.html", author=author, errors=errors)
