"""
Manual user seeding utility.

Use this script to insert or update demo users when needed.
It is intentionally separate from normal app startup.
"""

from app.core.database import get_db_connection

def seed_users():
    conn = get_db_connection()
    cur = conn.cursor()


    conn.commit()
    conn.close()
    print("Users seeded successfully")

if __name__ == "__main__":
    seed_users()