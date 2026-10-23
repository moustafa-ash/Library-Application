import click
import pymysql
from flask import current_app
from pymysql.constants import CLIENT


def get_connection(database=None):
    config = current_app.config
    return pymysql.connect(
        host=config["DB_HOST"],
        port=config["DB_PORT"],
        user=config["DB_USER"],
        password=config["DB_PASSWORD"],
        database=database if database is not None else config["DB_NAME"],
        cursorclass=pymysql.cursors.DictCursor,
        charset="utf8mb4",
        connect_timeout=5,
        # Unchanged updates still count as matching an existing row.
        client_flag=CLIENT.FOUND_ROWS,
    )


def init_app(app):
    @app.cli.command("check-db")
    def check_db():
        """Check both connections without creating tables or modifying data."""
        for label, database in (
            ("Authentication", app.config["AUTH_DB_NAME"]),
            ("Library", app.config["DB_NAME"]),
        ):
            try:
                with get_connection(database) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
            except pymysql.MySQLError:
                raise click.ClickException(
                    f"{label} database unavailable. Check website/.env and create the database using its setup SQL."
                ) from None
            click.echo(f"{label} database connection: OK")
