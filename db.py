import sqlite3

DB_NAME = "anime.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Table creation with real_filename column
    c.execute('''
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            title TEXT,
            real_filename TEXT, 
            file_size INTEGER,
            duration INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_anime(msg_id, title, real_filename, size, duration):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO anime (message_id, title, real_filename, file_size, duration) VALUES (?, ?, ?, ?, ?)",
                  (msg_id, title, real_filename, size, duration))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

def search_anime(query):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT message_id, title, real_filename, file_size, duration FROM anime WHERE title LIKE ? LIMIT 50", (f'%{query}%',))
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "filename": r[2], "size": r[3], "duration": r[4]} for r in rows]

def get_meta(msg_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT real_filename, file_size FROM anime WHERE message_id=?", (msg_id,))
    row = c.fetchone()
    conn.close()
    return row
