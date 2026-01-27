import sqlite3

DB_NAME = "anime.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            title TEXT,
            real_filename TEXT, 
            file_size INTEGER,
            duration INTEGER,
            poster TEXT,
            synopsis TEXT,
            rating TEXT,
            genres TEXT,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_anime(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO anime 
            (message_id, title, real_filename, file_size, duration, poster, synopsis, rating, genres, category) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['msg_id'], data['title'], data['filename'], data['size'], 0, 
              data['poster'], data['synopsis'], data['rating'], data['genres'], data['category']))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

# --- FIXED NAME HERE ---
def get_latest_anime():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM anime ORDER BY id DESC LIMIT 20")
    data = [dict(r) for r in c.fetchall()]
    conn.close()
    return data

def get_categories():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM anime")
    cats = [row[0] for row in c.fetchall()]
    conn.close()
    return cats

def search_anime(query):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM anime WHERE title LIKE ? OR category LIKE ? ORDER BY id DESC", (f'%{query}%', f'%{query}%'))
    data = [dict(r) for r in c.fetchall()]
    conn.close()
    return data

def get_anime_details(id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM anime WHERE id=?", (id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_meta(message_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT real_filename, file_size FROM anime WHERE message_id=?", (message_id,))
    row = c.fetchone()
    conn.close()
    return row
