"""Parameterized author and cascade-inspection queries."""


def list_authors(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT author_id, name, photo_filename FROM AUTHOR ORDER BY name, author_id")
        return cursor.fetchall()


def get_author(connection, author_id, *, lock=False):
    with connection.cursor() as cursor:
        cursor.execute("SELECT author_id, name, photo_filename FROM AUTHOR WHERE author_id = %s"
                       + (" FOR UPDATE" if lock else ""), (author_id,))
        return cursor.fetchone()


def insert_author(connection, name, photo_filename):
    with connection.cursor() as cursor:
        cursor.execute("INSERT INTO AUTHOR (name, photo_filename) VALUES (%s, %s)", (name, photo_filename))


def update_author(connection, author_id, name, photo_filename):
    with connection.cursor() as cursor:
        cursor.execute("UPDATE AUTHOR SET name = %s, photo_filename = %s WHERE author_id = %s",
                       (name, photo_filename, author_id))


def list_author_books(connection, author_id, *, lock=False):
    with connection.cursor() as cursor:
        cursor.execute("SELECT book_id, cover_filename FROM BOOK WHERE author_id = %s ORDER BY book_id"
                       + (" FOR UPDATE" if lock else ""), (author_id,))
        return cursor.fetchall()


def delete_author(connection, author_id):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM AUTHOR WHERE author_id = %s", (author_id,))
