from functools import wraps
import re

import bcrypt
import pymysql
from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .db import get_connection

auth = Blueprint("auth", __name__)
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))

        return view(*args, **kwargs)

    return wrapped_view


@auth.route("/register", methods=["GET", "POST"])
def register():
    errors = []

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name:
            errors.append("Name is required")
        if not email:
            errors.append("Email is required")
        if not password:
            errors.append("Password is required")
        if not confirm_password:
            errors.append("Confirm password is required")

        if password and confirm_password and password != confirm_password:
            errors.append("Passwords do not match")

        if len(name) > 100:
            errors.append("Name is too long (100 characters maximum)")

        if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errors.append("Enter a valid email address")

        if len(email) > 255:
            errors.append("Email is too long (255 characters maximum)")

        if len(password.encode("utf-8")) > 72:
            errors.append("Password is too long (72 bytes maximum)")

        if not errors:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
            try:
                with get_connection(current_app.config["AUTH_DB_NAME"]) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "INSERT INTO users (email, name, password_hash) "
                            "VALUES (%s, %s, %s)",
                            (email, name, password_hash),
                        )
                        user_id = cursor.lastrowid
                    connection.commit()

            except pymysql.MySQLError as error:
                if error.args[0] == 1062:
                    errors.append("Email already exists")
                else:
                    current_app.logger.exception("Registration database error")
                    errors.append("Unable to register right now. Please try again.")

            else:
                session.clear()
                session["user_id"] = user_id
                session["name"] = name
                current_app.session_interface.regenerate(session)
                return redirect(url_for("home"))

    return render_template("auth/register.html", errors=errors)


@auth.route("/login", methods=["GET", "POST"])
def login():
    errors = []

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email:
            errors.append("Email is required")
        if not password:
            errors.append("Password is required")

        if password and len(password.encode("utf-8")) > 72:
            errors.append("Invalid email or password")

        if not errors:
            try:
                with get_connection(current_app.config["AUTH_DB_NAME"]) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT user_id, name, password_hash "
                            "FROM users WHERE email = %s",
                            (email,),
                        )
                        user = cursor.fetchone()

            except pymysql.MySQLError:
                current_app.logger.exception("Login database error")
                errors.append("Unable to log in right now. Please try again.")

            else:
                try:
                    password_matches = user is not None and bcrypt.checkpw(
                        password.encode("utf-8"),
                        user["password_hash"].encode("utf-8"),
                    )
                except ValueError:
                    current_app.logger.exception("Invalid stored password hash")
                    password_matches = False

                if not password_matches:
                    errors.append("Invalid email or password")
                else:
                    session.clear()
                    session["user_id"] = user["user_id"]
                    session["name"] = user["name"]
                    current_app.session_interface.regenerate(session)
                    return redirect(url_for("home"))

    return render_template("auth/login.html", errors=errors)


@auth.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
