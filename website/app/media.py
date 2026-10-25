import re

from flask import Blueprint, abort, send_from_directory

from .auth import login_required
from .images import _directory

media = Blueprint("media", __name__)


@media.get("/media/<kind>/<filename>")
@login_required
def image(kind, filename):
    if kind not in ("books", "authors") or not re.fullmatch(r"[0-9a-f]{32}\.jpg", filename):
        abort(404)
    response = send_from_directory(_directory(kind), filename, mimetype="image/jpeg", conditional=True)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
