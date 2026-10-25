import secrets
from pathlib import Path

from cachelib.file import FileSystemCache
from flask import Flask, render_template, request, session
from flask_session import Session

from . import db
from .auth import auth, login_required
from .authors import authors
from .books import books
from .config import load_config, validate_config
from .media import media


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(load_config())
    if test_config is not None:
        app.config.update(test_config)
    validate_config(app.config)
    session_dir = Path(
        app.config.get("SESSION_FILE_DIR", Path(app.instance_path) / "sessions")
    )
    session_dir.mkdir(parents=True, exist_ok=True)
    app.config["SESSION_CACHELIB"] = FileSystemCache(str(session_dir))
    Session(app)
    db.init_app(app)
    app.register_blueprint(auth)
    app.register_blueprint(books)
    app.register_blueprint(authors)
    app.register_blueprint(media)
    if app.config.get("MAX_CONTENT_LENGTH") is None:
        app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

    @app.before_request
    def check_csrf_token():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            expected = session.get("csrf_token", "")
            submitted = request.form.get("csrf_token", "")
            if (
                not expected
                or not submitted
                or not secrets.compare_digest(
                    expected.encode("utf-8"), submitted.encode("utf-8")
                )
            ):
                return render_template("csrf_error.html"), 400

    @app.context_processor
    def inject_csrf_token():
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return {"csrf_token": session["csrf_token"]}

    @app.get("/")
    @login_required
    def home():
        return render_template("home.html")

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "error.html",
            code=404,
            heading="This page is unavailable",
            message="The link may be incorrect. Return to your library to continue.",
        ), 404

    @app.errorhandler(413)
    def request_too_large(error):
        return render_template(
            "error.html", code=413, heading="Upload is too large",
            message="Choose an image no larger than 5 MiB. The complete form request must be under 6 MiB.",
        ), 413

    @app.errorhandler(405)
    def method_not_allowed(error):
        return render_template(
            "error.html",
            code=405,
            heading="Please use the form on the page",
            message="Reopen the page and use its buttons to make this change.",
        ), 405

    @app.errorhandler(500)
    def server_error(error):
        return render_template(
            "error.html",
            code=500,
            heading="Something went wrong",
            message="Please reopen the page and try again.",
        ), 500

    return app
