from __future__ import annotations

import pytest

from app.sql_guard import guard_sql


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO orders(id) VALUES (999)",
        "UPDATE orders SET amount = 0",
        "DELETE FROM orders",
        "DROP TABLE orders",
        "SELECT * FROM orders; SELECT * FROM users;",
        "SELECT load_extension('x')",
        "SELECT randomblob(1000000)",
        "SELECT sqlite_version()",
        "SELECT * FROM sqlite_master",
        "SELECT * FROM pragma_database_list",
        "SELECT * FROM unknown_table",
    ],
)
def test_guard_rejects_unsafe_sql(sql: str) -> None:
    result = guard_sql(sql)
    assert result.allowed is False


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM orders LIMIT 3",
        "WITH recent AS (SELECT * FROM orders LIMIT 3) SELECT COUNT(*) FROM recent",
        "SELECT julianday(order_time) AS order_day FROM orders LIMIT 3",
    ],
)
def test_guard_allows_readonly_sql(sql: str) -> None:
    result = guard_sql(sql)
    assert result.allowed is True
    assert result.normalized_sql
