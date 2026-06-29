from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .config import DATA_DIR, DB_PATH


START_DATE = date(2026, 6, 5)
LAST_WINDOW_START = date(2026, 6, 12)
END_DATE = date(2026, 6, 18)

CHANNELS = [
    (1, "Douyin Ads", "paid_social"),
    (2, "WeChat Mini Program", "owned"),
    (3, "Organic Search", "organic"),
    (4, "Xiaohongshu", "paid_social"),
    (5, "Affiliate Partners", "partner"),
]

PRODUCTS = [
    (1, "Beauty", 189.0),
    (2, "Smart Home", 629.0),
    (3, "Sports", 259.0),
    (4, "Grocery", 79.0),
    (5, "Apparel", 329.0),
    (6, "Pet Care", 119.0),
    (7, "Electronics", 899.0),
    (8, "Home Cleaning", 139.0),
]

CITIES = ["上海", "北京", "广州", "深圳", "成都", "杭州"]
SEGMENTS = ["new", "growth", "vip", "at_risk"]

CHANNEL_PROFILES = {
    1: {"base_visits": 110, "prev_rate": 0.088, "last_rate": 0.108, "ticket": 1.13},
    2: {"base_visits": 86, "prev_rate": 0.072, "last_rate": 0.081, "ticket": 1.02},
    3: {"base_visits": 74, "prev_rate": 0.048, "last_rate": 0.056, "ticket": 0.96},
    4: {"base_visits": 98, "prev_rate": 0.082, "last_rate": 0.033, "ticket": 0.91},
    5: {"base_visits": 68, "prev_rate": 0.061, "last_rate": 0.044, "ticket": 1.08},
}


def init_db(force: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if force and DB_PATH.exists():
        DB_PATH.unlink()
    if DB_PATH.exists():
        return DB_PATH

    conn = sqlite3.connect(DB_PATH)
    try:
        _create_schema(conn)
        _seed_static_tables(conn)
        _seed_behavioral_data(conn)
        conn.commit()
    finally:
        conn.close()
    return DB_PATH


def writable_connection() -> sqlite3.Connection:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def read_only_connection() -> sqlite3.Connection:
    init_db()
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def execute_readonly_query(sql: str) -> dict[str, Any]:
    conn = read_only_connection()
    try:
        cursor = conn.execute(sql)
        rows = [dict(row) for row in cursor.fetchall()]
        columns = [column[0] for column in cursor.description or []]
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            city TEXT NOT NULL,
            segment TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );

        CREATE TABLE channels (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            price REAL NOT NULL
        );

        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            order_time TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('paid', 'refunded', 'cancelled')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (channel_id) REFERENCES channels(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY,
            channel_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            budget REAL NOT NULL,
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        );

        CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            event_time TEXT NOT NULL,
            event_type TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (channel_id) REFERENCES channels(id)
        );

        CREATE INDEX idx_orders_time ON orders(order_time);
        CREATE INDEX idx_orders_channel ON orders(channel_id);
        CREATE INDEX idx_events_time_type ON events(event_time, event_type);
        CREATE INDEX idx_events_channel ON events(channel_id);
        """
    )


def _seed_static_tables(conn: sqlite3.Connection) -> None:
    users = []
    signup_start = date(2026, 5, 20)
    for user_id in range(1, 181):
        city = CITIES[(user_id * 5) % len(CITIES)]
        segment = SEGMENTS[user_id % len(SEGMENTS)]
        signup = signup_start + timedelta(days=(user_id * 3) % 30)
        users.append((user_id, city, segment, signup.isoformat()))

    campaigns = [
        (1, 1, "618 Douyin GMV Sprint", "2026-06-10", "2026-06-18", 62000.0),
        (2, 2, "618 WeChat Member Day", "2026-06-10", "2026-06-18", 24000.0),
        (3, 3, "618 Organic SEO Topic", "2026-06-10", "2026-06-18", 7000.0),
        (4, 4, "618 Xiaohongshu KOL Burst", "2026-06-10", "2026-06-18", 42000.0),
        (5, 5, "618 Affiliate Rebate", "2026-06-10", "2026-06-18", 21000.0),
    ]

    conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", users)
    conn.executemany("INSERT INTO channels VALUES (?, ?, ?)", CHANNELS)
    conn.executemany("INSERT INTO products VALUES (?, ?, ?)", PRODUCTS)
    conn.executemany("INSERT INTO campaigns VALUES (?, ?, ?, ?, ?, ?)", campaigns)


def _seed_behavioral_data(conn: sqlite3.Connection) -> None:
    product_by_id = {product_id: (category, price) for product_id, category, price in PRODUCTS}
    event_id = 1
    order_id = 1
    day_count = (END_DATE - START_DATE).days + 1

    for offset in range(day_count):
        current_day = START_DATE + timedelta(days=offset)
        last_window = current_day >= LAST_WINDOW_START

        for channel_id, _name, _category in CHANNELS:
            profile = CHANNEL_PROFILES[channel_id]
            visits = profile["base_visits"] + (offset % 4) * 7 + channel_id * 3
            if channel_id == 4 and last_window:
                visits += 42
            if channel_id == 1 and last_window:
                visits += 18

            event_rows = []
            for visit_index in range(visits):
                user_id = ((visit_index * 11 + channel_id * 17 + offset * 19) % 180) + 1
                event_rows.append(
                    (
                        event_id,
                        user_id,
                        channel_id,
                        _timestamp(current_day, visit_index),
                        "visit",
                    )
                )
                event_id += 1
            conn.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?)", event_rows)

            rate = profile["last_rate"] if last_window else profile["prev_rate"]
            orders_count = max(1, round(visits * rate))
            for order_index in range(orders_count):
                user_id = ((order_index * 23 + channel_id * 13 + offset * 7) % 180) + 1
                product_id = _choose_product_id(channel_id, order_index, offset, last_window)
                product_category, base_price = product_by_id[product_id]
                quantity_factor = 1 + ((order_index + channel_id) % 3) * 0.38
                amount = round(base_price * quantity_factor * profile["ticket"], 2)
                status = _order_status(product_category, order_index, offset, channel_id, last_window)
                order_time = _timestamp(current_day, order_index + 200)
                conn.execute(
                    "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (order_id, user_id, channel_id, product_id, order_time, amount, status),
                )
                conn.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
                    (event_id, user_id, channel_id, order_time, "purchase"),
                )
                event_id += 1
                order_id += 1


def _timestamp(day: date, index: int) -> str:
    hour = 8 + (index % 12)
    minute = (index * 7) % 60
    second = (index * 13) % 60
    return datetime(day.year, day.month, day.day, hour, minute, second).isoformat(sep=" ")


def _choose_product_id(channel_id: int, order_index: int, offset: int, last_window: bool) -> int:
    if last_window and (order_index + channel_id + offset) % 5 == 0:
        return 2
    if channel_id == 1 and order_index % 4 == 0:
        return 7
    if channel_id == 2 and order_index % 3 == 0:
        return 1
    return ((order_index * 2 + channel_id + offset) % len(PRODUCTS)) + 1


def _order_status(
    product_category: str,
    order_index: int,
    offset: int,
    channel_id: int,
    last_window: bool,
) -> str:
    score = (order_index * 31 + offset * 17 + channel_id * 11) % 100
    refund_threshold = 4
    if product_category == "Smart Home" and last_window:
        refund_threshold = 28
    elif product_category == "Apparel" and last_window:
        refund_threshold = 10
    elif channel_id == 4 and last_window:
        refund_threshold = 8

    if score < refund_threshold:
        return "refunded"
    if score > 96:
        return "cancelled"
    return "paid"
