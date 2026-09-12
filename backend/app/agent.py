from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

from .database import execute_readonly_query
from .llm_client import ask_openai_compatible
from .schema_catalog import get_schema_catalog
from .sql_guard import GuardResult, guard_sql


AUDIT_LOGS: dict[str, list[dict[str, Any]]] = {}

SAMPLE_QUESTIONS = [
    "最近 7 天 GMV 最高的渠道是什么？",
    "哪个渠道转化率下降最多，可能原因是什么？",
    "618 活动期间 ROI 最好的渠道是哪几个？",
    "找出最近一周退款率异常升高的商品类别。",
    "新用户首单转化在不同城市有什么差异？",
]

LAST_START = "2026-06-12"
LAST_END = "2026-06-18"
PREV_START = "2026-06-05"
PREV_END = "2026-06-11"


def run_agent(question: str) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    steps: list[dict[str, Any]] = []
    AUDIT_LOGS[session_id] = []

    def record(kind: str, payload: dict[str, Any]) -> None:
        AUDIT_LOGS[session_id].append(
            {
                "kind": kind,
                "ts": datetime.now(timezone.utc).isoformat(),
                "payload": payload,
            }
        )

    schema = get_schema_catalog()
    steps.append(
        _step(
            "schema_retrieve",
            "completed",
            "已读取相关表结构、字段说明与样例值。",
            {"tables": [table["name"] for table in schema["tables"]]},
        )
    )
    record("schema_retrieve", {"table_count": len(schema["tables"])})

    plan = _plan_intent(question)
    steps.append(
        _step(
            "intent_plan",
            "completed",
            plan["summary"],
            {
                "metrics": plan["metrics"],
                "time_range": plan["time_range"],
                "clarification": plan.get("clarification"),
            },
        )
    )
    record("plan", plan)

    if _is_intro_question(question):
        answer = (
            "我是 DB Sentinel Agent，一个只读、安全、可审计的数据分析 Agent Demo。"
            "我可以基于内置 SQLite 示例库回答 GMV、渠道转化率、ROI、退款率和新用户首单转化等问题；"
            "不会执行写库、删表或修改数据的操作。"
        )
        steps.append(
            _step(
                "reflect_and_answer",
                "completed",
                "这是身份/能力范围问题，无需执行 SQL。",
                {"answer": answer},
            )
        )
        record("answer", {"answer": answer, "sql_executed": False})
        return {
            "session_id": session_id,
            "question": question,
            "steps": steps,
            "sql": "无需执行 SQL",
            "guard": {
                "allowed": True,
                "reason": "身份/能力范围问题，无需执行 SQL。",
                "normalized_sql": None,
            },
            "columns": [],
            "rows": [],
            "chart": None,
            "answer": answer,
            "suggestions": SAMPLE_QUESTIONS[:3],
            "blocked": False,
            "generated_by": "fallback",
            "sql_source": "not_applicable",
            "row_count": 0,
        }

    if not _looks_dangerous(question) and not _is_supported_analysis_question(question):
        llm_answer = _ask_llm_boundary_answer(question)
        answer = llm_answer or _unsupported_answer()
        source = "llm_boundary" if llm_answer else "not_applicable"
        generated_by = "llm" if llm_answer else "fallback"
        steps.append(
            _step(
                "reflect_and_answer",
                "completed",
                "当前问题不属于内置业务数据分析范围，无需执行 SQL。",
                {"answer": answer, "llm_available": bool(llm_answer)},
            )
        )
        record("answer", {"answer": answer, "sql_executed": False, "llm_available": bool(llm_answer)})
        return {
            "session_id": session_id,
            "question": question,
            "steps": steps,
            "sql": "无需执行 SQL",
            "guard": {
                "allowed": True,
                "reason": "非业务数据分析问题，无需执行 SQL。",
                "normalized_sql": None,
            },
            "columns": [],
            "rows": [],
            "chart": None,
            "answer": answer,
            "suggestions": SAMPLE_QUESTIONS[:3],
            "blocked": False,
            "generated_by": generated_by,
            "sql_source": source,
            "row_count": 0,
        }

    llm_hint = ask_openai_compatible(
        f"用户问题：{question}\n请生成只读 SQL 查询计划。若不确定，返回需要澄清的问题。"
    )
    sql, chart = _fallback_sql(question)
    steps.append(
        _step(
            "sql_generate",
            "completed",
            "已生成候选 SQL；当前使用规则 fallback，保证无 LLM key 时可演示。",
            {"llm_available": bool(llm_hint), "sql": sql},
        )
    )
    record("sql_generate", {"sql": sql, "llm_available": bool(llm_hint)})

    guard = guard_sql(sql)
    steps.append(
        _step(
            "sql_guard",
            "completed" if guard.allowed else "blocked",
            guard.reason,
            {"allowed": guard.allowed, "normalized_sql": guard.normalized_sql},
        )
    )
    record("guard", _guard_to_dict(guard))

    if not guard.allowed:
        answer = "只读安全拦截：该请求会触发写操作或危险 SQL，Agent 已停止执行。可以改问需要查询或分析的数据问题。"
        record("blocked_answer", {"answer": answer})
        return {
            "session_id": session_id,
            "question": question,
            "steps": steps,
            "sql": sql,
            "guard": _guard_to_dict(guard),
            "columns": [],
            "rows": [],
            "chart": None,
            "answer": answer,
            "suggestions": ["改为查询退款率、GMV、转化率或 ROI 等只读分析问题。"],
            "blocked": True,
            "generated_by": "fallback",
            "sql_source": "deterministic_fallback",
            "row_count": 0,
        }

    result = execute_readonly_query(guard.normalized_sql or sql)
    steps.append(
        _step(
            "execute_and_visualize",
            "completed",
            f"只读查询执行完成，返回 {result['row_count']} 行，并生成图表建议。",
            {"row_count": result["row_count"], "chart": chart},
        )
    )
    record("execution", result)

    answer = _answer(question, result["rows"])
    steps.append(
        _step(
            "reflect_and_answer",
            "completed",
            "已结合结果给出业务解释、异常洞察和数据限制。",
            {"answer": answer},
        )
    )
    record("answer", {"answer": answer})

    return {
        "session_id": session_id,
        "question": question,
        "steps": steps,
        "sql": guard.normalized_sql or sql,
        "guard": _guard_to_dict(guard),
        "columns": result["columns"],
        "rows": result["rows"],
        "chart": chart,
        "answer": answer,
        "suggestions": _suggestions(question),
        "blocked": False,
        "generated_by": "fallback",
        "sql_source": "deterministic_fallback",
        "row_count": result["row_count"],
    }


def get_audit(session_id: str) -> list[dict[str, Any]]:
    return AUDIT_LOGS.get(session_id, [])


def _step(name: str, status: str, summary: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "status": status, "summary": summary, "details": details}


def _guard_to_dict(guard: GuardResult) -> dict[str, Any]:
    return {
        "allowed": guard.allowed,
        "reason": guard.reason,
        "normalized_sql": guard.normalized_sql,
    }


def _plan_intent(question: str) -> dict[str, Any]:
    normalized = question.lower()
    if _looks_dangerous(question):
        return {
            "summary": "识别到用户可能要求写库或破坏数据，转入安全校验路径。",
            "metrics": ["sql_safety"],
            "time_range": "not_applicable",
        }
    if _is_intro_question(question):
        return {
            "summary": "识别为身份/能力范围问题，返回 Agent 能力说明和可尝试问题。",
            "metrics": ["agent_scope"],
            "time_range": "not_applicable",
        }
    if _is_roi_question(question):
        return {
            "summary": "按活动预算和活动期支付 GMV 计算渠道 ROI。",
            "metrics": ["campaign_revenue", "budget", "roi"],
            "time_range": "2026-06-10 至 2026-06-18",
        }
    if _is_conversion_question(question):
        return {
            "summary": "对比最近 7 天与前 7 天的渠道访问到下单转化率，寻找下降最大的渠道。",
            "metrics": ["visits", "orders", "conversion_rate", "delta"],
            "time_range": f"{PREV_START} 至 {LAST_END}",
        }
    if _is_refund_question(question):
        return {
            "summary": "按商品类别对比最近一周与前一周退款率，定位异常升高类别。",
            "metrics": ["refund_rate", "refund_delta"],
            "time_range": f"{PREV_START} 至 {LAST_END}",
        }
    if _is_city_question(question):
        return {
            "summary": "按城市统计新注册用户在 7 天内完成首单的比例。",
            "metrics": ["new_users", "converted_users", "first_order_conversion"],
            "time_range": "注册日期 2026-06-01 之后",
        }
    if _is_gmv_reason_question(question):
        return {
            "summary": "围绕 GMV 领先渠道拆解订单量、客单价和退款影响，解释领先原因。",
            "metrics": ["paid_orders", "avg_order_value", "refund_orders", "gmv"],
            "time_range": f"{LAST_START} 至 {LAST_END}",
        }
    if _is_segment_question(question):
        return {
            "summary": "按渠道和商品类别细分最近 7 天 paid GMV，定位主要贡献结构。",
            "metrics": ["channel", "product_category", "paid_orders", "gmv"],
            "time_range": f"{LAST_START} 至 {LAST_END}",
        }
    if _is_sql_export_question(question):
        return {
            "summary": "生成可复核的只读 SQL，并返回关键字段说明，方便数据同学二次校验。",
            "metrics": ["gmv", "paid_orders", "sql_review"],
            "time_range": f"{LAST_START} 至 {LAST_END}",
        }
    if not _is_default_gmv_question(question):
        return {
            "summary": "当前问题不属于内置业务数据分析范围，返回边界说明而不是套用默认 GMV 模版。",
            "metrics": ["out_of_scope"],
            "time_range": "not_applicable",
        }
    return {
        "summary": "默认拆解为最近 7 天渠道 GMV 排名问题。",
        "metrics": ["gmv", "paid_orders"],
        "time_range": f"{LAST_START} 至 {LAST_END}",
    }


def _fallback_sql(question: str) -> tuple[str, dict[str, Any] | None]:
    if _looks_dangerous(question):
        return "DROP TABLE orders;", None

    normalized = question.lower()
    if _is_roi_question(question):
        return (
            """
            SELECT
                c.name AS channel,
                ROUND(SUM(CASE WHEN o.status = 'paid' THEN o.amount ELSE 0 END), 2) AS revenue,
                ca.budget AS budget,
                ROUND(SUM(CASE WHEN o.status = 'paid' THEN o.amount ELSE 0 END) / ca.budget, 2) AS roi
            FROM campaigns ca
            JOIN channels c ON c.id = ca.channel_id
            LEFT JOIN orders o
                ON o.channel_id = ca.channel_id
                AND date(o.order_time) BETWEEN ca.start_date AND ca.end_date
            WHERE ca.name LIKE '%618%'
            GROUP BY c.id, c.name, ca.budget
            ORDER BY roi DESC
            LIMIT 5
            """,
            {"type": "bar", "title": "618 活动渠道 ROI", "xKey": "channel", "yKeys": ["roi"]},
        )

    if _is_conversion_question(question):
        return (
            f"""
            WITH channel_windows AS (
                SELECT
                    c.id AS channel_id,
                    c.name AS channel,
                    SUM(CASE WHEN date(e.event_time) BETWEEN '{PREV_START}' AND '{PREV_END}' AND e.event_type = 'visit' THEN 1 ELSE 0 END) AS prev_visits,
                    SUM(CASE WHEN date(e.event_time) BETWEEN '{LAST_START}' AND '{LAST_END}' AND e.event_type = 'visit' THEN 1 ELSE 0 END) AS last_visits
                FROM channels c
                LEFT JOIN events e ON e.channel_id = c.id
                GROUP BY c.id, c.name
            ),
            order_windows AS (
                SELECT
                    c.id AS channel_id,
                    SUM(CASE WHEN date(o.order_time) BETWEEN '{PREV_START}' AND '{PREV_END}' AND o.status IN ('paid', 'refunded') THEN 1 ELSE 0 END) AS prev_orders,
                    SUM(CASE WHEN date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}' AND o.status IN ('paid', 'refunded') THEN 1 ELSE 0 END) AS last_orders
                FROM channels c
                LEFT JOIN orders o ON o.channel_id = c.id
                GROUP BY c.id
            )
            SELECT
                cw.channel,
                prev_visits,
                prev_orders,
                ROUND(100.0 * prev_orders / NULLIF(prev_visits, 0), 2) AS prev_conversion_rate,
                last_visits,
                last_orders,
                ROUND(100.0 * last_orders / NULLIF(last_visits, 0), 2) AS last_conversion_rate,
                ROUND(100.0 * last_orders / NULLIF(last_visits, 0) - 100.0 * prev_orders / NULLIF(prev_visits, 0), 2) AS delta_percentage_points
            FROM channel_windows cw
            JOIN order_windows ow ON ow.channel_id = cw.channel_id
            ORDER BY delta_percentage_points ASC
            LIMIT 5
            """,
            {
                "type": "bar",
                "title": "渠道转化率变化（百分点）",
                "xKey": "channel",
                "yKeys": ["delta_percentage_points"],
            },
        )

    if _is_refund_question(question):
        return (
            f"""
            WITH category_orders AS (
                SELECT
                    p.category AS product_category,
                    SUM(CASE WHEN date(o.order_time) BETWEEN '{PREV_START}' AND '{PREV_END}' THEN 1 ELSE 0 END) AS prev_orders,
                    SUM(CASE WHEN date(o.order_time) BETWEEN '{PREV_START}' AND '{PREV_END}' AND o.status = 'refunded' THEN 1 ELSE 0 END) AS prev_refunds,
                    SUM(CASE WHEN date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}' THEN 1 ELSE 0 END) AS last_orders,
                    SUM(CASE WHEN date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}' AND o.status = 'refunded' THEN 1 ELSE 0 END) AS last_refunds
                FROM orders o
                JOIN products p ON p.id = o.product_id
                GROUP BY p.category
            )
            SELECT
                product_category,
                prev_orders,
                prev_refunds,
                ROUND(100.0 * prev_refunds / NULLIF(prev_orders, 0), 2) AS prev_refund_rate,
                last_orders,
                last_refunds,
                ROUND(100.0 * last_refunds / NULLIF(last_orders, 0), 2) AS last_refund_rate,
                ROUND(100.0 * last_refunds / NULLIF(last_orders, 0) - 100.0 * prev_refunds / NULLIF(prev_orders, 0), 2) AS delta_percentage_points
            FROM category_orders
            WHERE last_orders >= 3
            ORDER BY delta_percentage_points DESC
            LIMIT 5
            """,
            {
                "type": "bar",
                "title": "商品类别退款率上升（百分点）",
                "xKey": "product_category",
                "yKeys": ["delta_percentage_points"],
            },
        )

    if _is_city_question(question):
        return (
            """
            WITH first_paid_order AS (
                SELECT
                    user_id,
                    MIN(date(order_time)) AS first_order_date
                FROM orders
                WHERE status = 'paid'
                GROUP BY user_id
            )
            SELECT
                u.city,
                COUNT(*) AS new_users,
                SUM(CASE
                    WHEN f.first_order_date IS NOT NULL
                        AND julianday(f.first_order_date) - julianday(u.signup_date) BETWEEN 0 AND 7
                    THEN 1 ELSE 0 END
                ) AS converted_users,
                ROUND(100.0 * SUM(CASE
                    WHEN f.first_order_date IS NOT NULL
                        AND julianday(f.first_order_date) - julianday(u.signup_date) BETWEEN 0 AND 7
                    THEN 1 ELSE 0 END
                ) / COUNT(*), 2) AS first_order_conversion_rate
            FROM users u
            LEFT JOIN first_paid_order f ON f.user_id = u.id
            WHERE date(u.signup_date) >= '2026-06-01'
            GROUP BY u.city
            ORDER BY first_order_conversion_rate DESC
            """,
            {
                "type": "bar",
                "title": "新用户首单转化率（%）",
                "xKey": "city",
                "yKeys": ["first_order_conversion_rate"],
            },
        )

    if _is_gmv_reason_question(question):
        return (
            f"""
            SELECT
                c.name AS channel,
                COUNT(CASE WHEN o.status = 'paid' THEN 1 END) AS paid_orders,
                ROUND(SUM(CASE WHEN o.status = 'paid' THEN o.amount ELSE 0 END), 2) AS gmv,
                ROUND(AVG(CASE WHEN o.status = 'paid' THEN o.amount END), 2) AS avg_order_value,
                COUNT(CASE WHEN o.status = 'refunded' THEN 1 END) AS refund_orders
            FROM orders o
            JOIN channels c ON c.id = o.channel_id
            WHERE date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}'
            GROUP BY c.id, c.name
            ORDER BY gmv DESC
            LIMIT 5
            """,
            {
                "type": "bar",
                "title": "渠道 GMV 领先原因拆解",
                "xKey": "channel",
                "yKeys": ["gmv", "avg_order_value"],
            },
        )

    if _is_segment_question(question):
        return (
            f"""
            SELECT
                c.name AS channel,
                p.category AS product_category,
                COUNT(*) AS paid_orders,
                ROUND(SUM(o.amount), 2) AS gmv
            FROM orders o
            JOIN channels c ON c.id = o.channel_id
            JOIN products p ON p.id = o.product_id
            WHERE o.status = 'paid'
                AND date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}'
            GROUP BY c.id, c.name, p.category
            ORDER BY gmv DESC
            LIMIT 10
            """,
            {
                "type": "bar",
                "title": "渠道 x 商品类别 GMV 细分",
                "xKey": "product_category",
                "yKeys": ["gmv"],
            },
        )

    if _is_sql_export_question(question):
        return (
            f"""
            SELECT
                c.name AS channel,
                COUNT(*) AS paid_orders,
                ROUND(SUM(o.amount), 2) AS gmv,
                MIN(date(o.order_time)) AS start_date,
                MAX(date(o.order_time)) AS end_date
            FROM orders o
            JOIN channels c ON c.id = o.channel_id
            WHERE o.status = 'paid'
                AND date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}'
            GROUP BY c.id, c.name
            ORDER BY gmv DESC
            LIMIT 5
            """,
            {"type": "bar", "title": "SQL 复核口径：渠道 GMV", "xKey": "channel", "yKeys": ["gmv"]},
        )

    return (
        f"""
        SELECT
            c.name AS channel,
            COUNT(*) AS paid_orders,
            ROUND(SUM(o.amount), 2) AS gmv
        FROM orders o
        JOIN channels c ON c.id = o.channel_id
        WHERE o.status = 'paid'
            AND date(o.order_time) BETWEEN '{LAST_START}' AND '{LAST_END}'
        GROUP BY c.id, c.name
        ORDER BY gmv DESC
        LIMIT 5
        """,
        {"type": "bar", "title": "最近 7 天渠道 GMV（元）", "xKey": "channel", "yKeys": ["gmv"]},
    )


def _answer(question: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "查询没有返回结果。建议扩大时间范围，或检查相关渠道、商品类别是否有数据。"

    top = rows[0]
    if _is_roi_question(question):
        return (
            f"618 活动期间 ROI 最高的是 {top['channel']}，ROI 约为 {top['roi']}。"
            "口径为活动期内 paid 订单 GMV / 活动预算；该口径未扣除履约成本，适合做渠道初筛。"
        )
    if _is_conversion_question(question):
        return (
            f"转化率下降最多的是 {top['channel']}，变化 {top['delta_percentage_points']} 个百分点。"
            f"它最近 7 天访问量为 {top['last_visits']}，但成交订单只有 {top['last_orders']}；"
            "可能原因是流量质量下降、投放人群偏移或落地页/库存问题。建议继续按素材、城市和商品类别拆分。"
        )
    if _is_refund_question(question):
        return (
            f"退款率异常升高最明显的是 {top['product_category']}，"
            f"最近一周退款率 {top['last_refund_rate']}%，较前一周变化 {top['delta_percentage_points']} 个百分点。"
            "建议核查该品类近期批次质量、页面承诺和售后原因。"
        )
    if _is_city_question(question):
        return (
            f"新用户首单转化率最高的城市是 {top['city']}，转化率 {top['first_order_conversion_rate']}%。"
            "不同城市差异可能来自渠道结构、物流承诺和本地活动触达，建议进一步拆到渠道维度。"
        )
    if _is_gmv_reason_question(question):
        return (
            f"{top['channel']} 的 GMV 领先主要来自 paid 订单数 {top['paid_orders']}、"
            f"平均客单价 {top['avg_order_value']}，最近 7 天 paid GMV 为 {top['gmv']}。"
            f"同期退款订单数为 {top['refund_orders']}，建议继续核查该渠道的人群质量、活动素材和高客单商品占比。"
        )
    if _is_segment_question(question):
        return (
            f"最近 7 天贡献最高的细分组合是 {top['channel']} / {top['product_category']}，"
            f"GMV 为 {top['gmv']}，paid 订单数 {top['paid_orders']}。"
            "这说明渠道表现不能只看总量，还应拆到商品类别评估结构性贡献。"
        )
    if _is_sql_export_question(question):
        return (
            f"已生成可复核 SQL：口径为 {top['start_date']} 至 {top['end_date']} 的 paid 订单 GMV，"
            f"当前最高渠道为 {top['channel']}，GMV {top['gmv']}，paid 订单数 {top['paid_orders']}。"
            "页面中的 SQL 可直接复制给数据同学复核。"
        )
    return (
        f"最近 7 天 GMV 最高的渠道是 {top['channel']}，GMV 为 {top['gmv']}，"
        f"paid 订单数 {top['paid_orders']}。该结论基于 paid 订单，不包含退款和取消订单。"
    )


def _suggestions(question: str) -> list[str]:
    if _is_conversion_question(question):
        return ["继续按城市拆分下降渠道", "查看下降渠道的商品类别结构", "对比活动前后退款率"]
    if _is_refund_question(question):
        return ["按渠道查看该品类退款率", "查看退款订单金额分布", "对比该品类 GMV 与退款率"]
    if _is_gmv_reason_question(question):
        return ["按商品类别细分 Douyin Ads 的 GMV", "对比 Douyin Ads 与 Xiaohongshu 的客单价", "导出当前分析 SQL"]
    if _is_segment_question(question):
        return ["继续看退款率异常品类", "按城市拆分新用户首单转化", "导出当前分析 SQL"]
    if _is_sql_export_question(question):
        return ["查看 SQL guard 审计记录", "按商品类别细分结果", "继续追问原因拆解"]
    return ["继续追问原因拆解", "按城市或商品类别细分", "导出 SQL 给数据同学复核"]


def _ask_llm_boundary_answer(question: str) -> str | None:
    answer = ask_openai_compatible(
        (
            "用户输入不属于当前内置 SQLite 业务数据分析问题。\n"
            f"用户输入：{question}\n"
            "请用中文简短回复：说明你是 DB Sentinel Agent，当前只能回答内置 Demo 数据中的 GMV、"
            "渠道转化率、ROI、退款率、新用户首单转化和 SQL 复核问题；不要编造业务数据结论。"
        ),
        system_prompt=(
            "你是 DB Sentinel Agent 的边界回复模块。只输出自然语言短句，不输出 JSON，"
            "不生成 SQL，不提供与内置 Demo 无关的建议。"
        ),
        temperature=0.2,
    )
    if not answer:
        return None
    return answer.strip()[:500]


def _unsupported_answer() -> str:
    return (
        "这个问题不在当前 DB Sentinel Agent Demo 的数据分析范围内。"
        "我可以回答内置 SQLite 示例库中的 GMV、渠道转化率、ROI、退款率、"
        "新用户首单转化和 SQL 复核问题；不会为了无关问题套用默认 GMV 模版。"
    )


def _is_supported_analysis_question(question: str) -> bool:
    return (
        _is_roi_question(question)
        or _is_conversion_question(question)
        or _is_refund_question(question)
        or _is_city_question(question)
        or _is_gmv_reason_question(question)
        or _is_segment_question(question)
        or _is_sql_export_question(question)
        or _is_default_gmv_question(question)
    )


def _is_intro_question(question: str) -> bool:
    normalized = question.strip().lower()
    intro_phrases = {"你好", "您好", "hi", "hello", "你是谁", "你是啥", "介绍一下", "你能做什么"}
    return normalized in intro_phrases or any(phrase in question for phrase in ["你是谁", "你能做什么", "介绍一下"])


def _is_roi_question(question: str) -> bool:
    return "roi" in question.lower() or "618" in question


def _is_conversion_question(question: str) -> bool:
    return "转化" in question or "下降" in question


def _is_refund_question(question: str) -> bool:
    return "退款" in question


def _is_city_question(question: str) -> bool:
    if _is_segment_question(question):
        return False
    return "城市" in question or "首单" in question or "新用户" in question


def _is_segment_question(question: str) -> bool:
    return "细分" in question or "商品类别" in question or "品类" in question


def _is_sql_export_question(question: str) -> bool:
    return "导出" in question or "复核" in question or "sql" in question.lower()


def _is_gmv_reason_question(question: str) -> bool:
    normalized = question.lower()
    if _is_conversion_question(question) or _is_refund_question(question) or _is_roi_question(question):
        return False
    return "原因" in question or "拆解" in question or "why" in normalized


def _is_default_gmv_question(question: str) -> bool:
    normalized = question.lower()
    gmv_terms = ("gmv", "销售额", "成交额", "交易额", "订单金额")
    rank_terms = ("最高", "最多", "排名", "排行", "top", "领先")
    return ("渠道" in question and any(term in normalized for term in gmv_terms)) or (
        any(term in normalized for term in gmv_terms) and any(term in question.lower() for term in rank_terms)
    )


def _looks_dangerous(question: str) -> bool:
    lowered = question.lower()
    dangerous_words = [
        "insert",
        "update",
        "delete",
        "drop",
        "alter",
        "truncate",
        "attach",
        "detach",
        "清空",
        "删除",
        "删表",
        "改表",
        "写入",
        "插入",
        "更新",
    ]
    return any(re.search(rf"\b{re.escape(word)}\b", lowered) for word in dangerous_words) or any(
        word in question for word in dangerous_words[-7:]
    )
