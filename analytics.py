import sqlite3
import threading
import os

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'analytics.db')
_write_lock = threading.Lock()
_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init_db():
    conn = _get_conn()
    with _write_lock:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                ip_hash TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()


def record_event(event_type, ip_hash, user_agent):
    conn = _get_conn()
    with _write_lock:
        conn.execute(
            'INSERT INTO analytics_events (event_type, ip_hash, user_agent) VALUES (?, ?, ?)',
            (event_type, ip_hash, user_agent)
        )
        conn.commit()


def get_stats():
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'page_view'")
    total_views = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT ip_hash) FROM analytics_events WHERE event_type = 'visitor'")
    total_visitors = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'download_click'")
    total_download_clicks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'download_success'")
    total_download_success = cur.fetchone()[0]

    total_downloads = total_download_clicks + total_download_success

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'instagram_click'")
    instagram_clicks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'telegram_click'")
    telegram_clicks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'whatsapp_click'")
    whatsapp_clicks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'lynkid_click'")
    lynkid_clicks = cur.fetchone()[0]

    total_social_clicks = instagram_clicks + telegram_clicks + whatsapp_clicks + lynkid_clicks

    return {
        'total_views': total_views,
        'total_visitors': total_visitors,
        'total_downloads': total_downloads,
        'total_download_clicks': total_download_clicks,
        'total_download_success': total_download_success,
        'total_social_clicks': total_social_clicks,
        'instagram_clicks': instagram_clicks,
        'telegram_clicks': telegram_clicks,
        'whatsapp_clicks': whatsapp_clicks,
        'lynkid_clicks': lynkid_clicks,
    }


def get_detailed_stats():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT event_type, COUNT(*) as count FROM analytics_events GROUP BY event_type ORDER BY count DESC")
    rows = cur.fetchall()
    return [{'event_type': row[0], 'count': row[1]} for row in rows]
