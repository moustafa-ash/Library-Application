"""Parameterized book operations; the route owns the connection/transaction."""


def list_books(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT book_id, title, price, author_id, cover_filename FROM BOOK ORDER BY book_id")
        return cursor.fetchall()


def get_book(connection, book_id, *, lock=False):
    with connection.cursor() as cursor:
        cursor.execute("SELECT book_id, title, price, author_id, cover_filename FROM BOOK "
                       "WHERE book_id = %s" + (" FOR UPDATE" if lock else ""), (book_id,))
        return cursor.fetchone()


def list_authors(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT author_id, name FROM AUTHOR ORDER BY name, author_id")
        return cursor.fetchall()


def author_exists(connection, author_id):
    with connection.cursor() as cursor:
        cursor.execute("SELECT author_id FROM AUTHOR WHERE author_id = %s", (author_id,))
        return cursor.fetchone() is not None


def insert_book(connection, title, price, author_id, cover_filename):
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO BOOK (title, price, author_id, cover_filename) VALUES (%s, %s, %s, %s)",
                       (title, price, author_id, cover_filename))


def update_book(connection, book_id, title, price, author_id, cover_filename):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE BOOK SET title = %s, price = %s, author_id = %s, cover_filename = %s "
                       "WHERE book_id = %s", (title, price, author_id, cover_filename, book_id))


def delete_book(connection, book_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM BOOK WHERE book_id = %s", (book_id,))
