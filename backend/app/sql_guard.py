from __future__ import annotations

from dataclasses import dataclass

from sqlglot import exp, parse


DANGEROUS_EXPRESSIONS = (
    exp.Alter,
    exp.Command,
    exp.Create,
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Merge,
    exp.TruncateTable,
    exp.Update,
)

DANGEROUS_FUNCTIONS = {
    "attach",
    "detach",
    "load_extension",
    "randomblob",
    "readfile",
    "sqlite_version",
    "zeroblob",
    "writefile",
}

ALLOWED_ANONYMOUS_FUNCTIONS = {
    "julianday",
}

ALLOWED_TABLES = {
    "campaigns",
    "channels",
    "events",
    "orders",
    "products",
    "users",
}

DENIED_TABLE_PREFIXES = ("sqlite_", "pragma_")
DENIED_TABLES = {
    "pragma_database_list",
    "sqlite_master",
    "sqlite_schema",
    "sqlite_temp_master",
}


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str
    normalized_sql: str | None = None


def guard_sql(sql: str) -> GuardResult:
    candidate = sql.strip()
    if not candidate:
        return GuardResult(False, "SQL 为空")

    try:
        expressions = parse(candidate, read="sqlite")
    except Exception as exc:  # pragma: no cover - sqlglot exception types vary
        return GuardResult(False, f"SQL 解析失败：{exc}")

    if len(expressions) != 1:
        return GuardResult(False, "拒绝多语句执行，只允许单条只读查询")

    expression = expressions[0]
    if not isinstance(expression, (exp.Select, exp.Union)):
        return GuardResult(False, "只允许 SELECT / WITH 只读查询")

    for node in expression.walk():
        if isinstance(node, DANGEROUS_EXPRESSIONS):
            return GuardResult(False, f"检测到危险 SQL 节点：{node.key.upper()}")

        if isinstance(node, exp.Anonymous):
            function_name = node.name.lower()
            if function_name in DANGEROUS_FUNCTIONS:
                return GuardResult(False, f"拒绝危险函数：{function_name}")
            if function_name not in ALLOWED_ANONYMOUS_FUNCTIONS:
                return GuardResult(False, f"拒绝未纳入白名单的函数：{function_name}")

    cte_names = {
        cte.alias_or_name.lower()
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }
    for table in expression.find_all(exp.Table):
        table_name = table.name.lower()
        if table.args.get("db") or table.args.get("catalog"):
            return GuardResult(False, "拒绝跨数据库或带 schema 的表引用")
        if table_name in cte_names:
            continue
        if table_name in DENIED_TABLES or table_name.startswith(DENIED_TABLE_PREFIXES):
            return GuardResult(False, f"拒绝访问 SQLite 内部表或 pragma：{table_name}")
        if table_name not in ALLOWED_TABLES:
            return GuardResult(False, f"拒绝访问未授权业务表：{table_name}")

    normalized = expression.sql(dialect="sqlite")
    return GuardResult(True, "SQL guard 通过：单条只读 SELECT/WITH 查询", normalized)
