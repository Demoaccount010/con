import sqlite3
import re

DB_NAME = "anime.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER UNIQUE,
            title TEXT,
            series_name TEXT,
            episode_num INTEGER,
            real_filename TEXT, 
            file_size INTEGER,
            duration INTEGER,
            poster TEXT,
            synopsis TEXT,
            rating TEXT,
            genres TEXT,
            extra_info TEXT,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_anime(data):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Auto Detect Series Name & Episode
    # Ex: "Naruto Shippuden - S01E05" -> Series: Naruto Shippuden, Ep: 5
    clean_title = data['title']
    ep_num = 1
    series_name = clean_title

    # Regex to find episode number (E05, Ep 5, Episode 5, - 05)
    match = re.search(r'(?:ep|episode|e|\s-)\s*(\d+)', clean_title, re.IGNORECASE)
    if match:
        ep_num = int(match.group(1))
        # Remove Ep number from series name to group them
        series_name = clean_title[:match.start()].strip().strip('-')

    try:
        c.execute("""
            INSERT OR IGNORE INTO anime 
            (message_id, title, series_name, episode_num, real_filename, file_size, duration, poster, synopsis, rating, genres, extra_info, category) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data['msg_id'], data['title'], series_name, ep_num, data['filename'], data['size'], 0, 
              data['poster'], data['synopsis'], data['rating'], data['genres'], data.get('extra_info', ''), data['category']))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        conn.close()

def get_latest():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Group by Series to show only 1 card per series on home
    c.execute("SELECT * FROM anime GROUP BY series_name ORDER BY id DESC LIMIT 20")
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
    c.execute("SELECT * FROM anime WHERE title LIKE ? OR series_name LIKE ? GROUP BY series_name ORDER BY id DESC", (f'%{query}%', f'%{query}%'))
    data = [dict(r) for r in c.fetchall()]
    conn.close()
    return data

def get_details(id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get Current Video
    c.execute("SELECT * FROM anime WHERE id=?", (id,))
    current = c.fetchone()
    if not current: return None
    
    current = dict(current)
    
    # Get All Episodes of Same Series
    c.execute("SELECT id, title, episode_num FROM anime WHERE series_name=? ORDER BY episode_num ASC", (current['series_name'],))
    episodes = [dict(r) for r in c.fetchall()]
    
    current['episodes'] = episodes
    
    # Find Next/Prev
    current_ep_num = current['episode_num']
    current['next_id'] = next((e['id'] for e in episodes if e['episode_num'] > current_ep_num), None)
    current['prev_id'] = next((e['id'] for e in episodes[::-1] if e['episode_num'] < current_ep_num), None)
    
    conn.close()
    return current

def get_meta(message_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT real_filename, file_size FROM anime WHERE message_id=?", (message_id,))
    row = c.fetchone()
    conn.close()
    return row
