import sqlite3

from app.config import settings

def get_user(username):

    print(f"Searching user: {username}")
    print(f"Using DB: {settings.DB_PATH}")

    conn = sqlite3.connect(settings.DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            username,
            password_hash,
            role,
            full_name
        FROM users
        WHERE username = ?
        """,
        (username,)
    )

    row = cursor.fetchone()

    conn.close()

    print("DB row:", row)

    if not row:
        return None

    return {
        "username": row[0],
        "password_hash": row[1],
        "role": row[2],
        "full_name": row[3]
    }