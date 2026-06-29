from __future__ import annotations

from typing import Any

from .config import DB_PATH, DEMO_TODAY
from .database import read_only_connection


TABLE_DESCRIPTIONS = {
    "users": "用户维表，包含城市、生命周期分层和注册日期。",
    "channels": "渠道维表，区分付费投放、自有渠道、自然流量和联盟渠道。",
    "products": "商品维表，包含商品类别和标准价格。",
    "orders": "订单事实表，记录订单金额、渠道、商品、下单时间和支付/退款/取消状态。",
    "campaigns": "营销活动表，记录 618 活动周期、预算和绑定渠道。",
    "events": "用户行为事件表，包含访问和购买事件，用于估算渠道转化率。",
}

COLUMN_DESCRIPTIONS = {
    "users.id": "用户唯一 ID",
    "users.city": "用户所在城市",
    "users.segment": "用户生命周期分层",
    "users.signup_date": "注册日期",
    "channels.id": "渠道唯一 ID",
    "channels.name": "渠道名称",
    "channels.category": "渠道类型",
    "products.id": "商品唯一 ID",
    "products.category": "商品类别",
    "products.price": "商品标准价格",
    "orders.id": "订单唯一 ID",
    "orders.user_id": "下单用户 ID",
    "orders.channel_id": "订单归因渠道 ID",
    "orders.product_id": "订单商品 ID",
    "orders.order_time": "下单时间",
    "orders.amount": "订单金额",
    "orders.status": "订单状态：paid/refunded/cancelled",
    "campaigns.id": "活动唯一 ID",
    "campaigns.channel_id": "活动绑定渠道 ID",
    "campaigns.name": "活动名称",
    "campaigns.start_date": "活动开始日期",
    "campaigns.end_date": "活动结束日期",
    "campaigns.budget": "活动预算",
    "events.id": "事件唯一 ID",
    "events.user_id": "事件用户 ID",
    "events.channel_id": "事件归因渠道 ID",
    "events.event_time": "事件发生时间",
    "events.event_type": "事件类型：visit/purchase",
}


def get_schema_catalog() -> dict[str, Any]:
    conn = read_only_connection()
    try:
        tables = []
        for table_name in TABLE_DESCRIPTIONS:
            columns = []
            pragma_rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            for row in pragma_rows:
                column_name = row["name"]
                sample_rows = conn.execute(
                    f"SELECT DISTINCT {column_name} AS value FROM {table_name} "
                    f"WHERE {column_name} IS NOT NULL LIMIT 5"
                ).fetchall()
                samples = [sample["value"] for sample in sample_rows]
                columns.append(
                    {
                        "name": column_name,
                        "type": row["type"],
                        "description": COLUMN_DESCRIPTIONS.get(
                            f"{table_name}.{column_name}", ""
                        ),
                        "sample_values": samples,
                    }
                )

            count = conn.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()[
                "count"
            ]
            tables.append(
                {
                    "name": table_name,
                    "description": TABLE_DESCRIPTIONS[table_name],
                    "row_count": count,
                    "columns": columns,
                }
            )
        return {
            "database": DB_PATH.name,
            "mode": "readonly",
            "business_date": DEMO_TODAY,
            "tables": tables,
        }
    finally:
        conn.close()
