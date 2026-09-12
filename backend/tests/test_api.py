from __future__ import annotations

from fastapi.testclient import TestClient

from app import agent as agent_module
from app.database import init_db
from app import main as main_module
from app.main import app


client = TestClient(app)


def setup_module() -> None:
    init_db(force=True)


def test_schema_returns_complete_catalog() -> None:
    response = client.get("/api/schema")
    assert response.status_code == 200
    body = response.json()
    table_names = {table["name"] for table in body["tables"]}
    assert {"users", "channels", "products", "orders", "campaigns", "events"} <= table_names
    assert body["mode"] == "readonly"
    assert len(body["sample_questions"]) == 5


def test_config_returns_runtime_endpoints() -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert body["configFile"] == "config/app.conf"
    assert body["database"]["mode"] == "readonly"
    assert body["database"]["resetEnabled"] is False
    assert body["apiDisplay"]


def test_chat_fallback_answers_sample_question() -> None:
    response = client.post("/api/chat", json={"question": "最近 7 天 GMV 最高的渠道是什么？"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is False
    assert body["guard"]["allowed"] is True
    assert body["rows"]
    assert "GMV" in body["answer"]
    assert {step["name"] for step in body["steps"]} == {
        "schema_retrieve",
        "intent_plan",
        "sql_generate",
        "sql_guard",
        "execute_and_visualize",
        "reflect_and_answer",
    }


def test_chat_blocks_dangerous_request_without_execution() -> None:
    response = client.post("/api/chat", json={"question": "帮我 drop table orders"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is True
    assert body["guard"]["allowed"] is False
    assert body["rows"] == []
    assert "只读安全拦截" in body["answer"]


def test_follow_up_question_uses_distinct_analysis() -> None:
    response = client.post("/api/chat", json={"question": "继续追问原因拆解"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is False
    assert body["rows"]
    assert "avg_order_value" in body["columns"]
    assert "原因" in body["answer"] or "领先" in body["answer"]
    assert "平均客单价" in body["answer"]


def test_segment_follow_up_does_not_fall_back_to_default_gmv() -> None:
    response = client.post("/api/chat", json={"question": "按城市或商品类别细分"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is False
    assert "product_category" in body["columns"]
    assert "细分" in body["answer"]
    assert "GROUP BY c.id, c.name, p.category" in body["sql"]


def test_conversion_drop_question_keeps_conversion_intent() -> None:
    response = client.post("/api/chat", json={"question": "哪个渠道转化率下降最多，可能原因是什么？"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is False
    assert "delta_percentage_points" in body["columns"]
    assert "转化率下降最多" in body["answer"]
    assert "avg_order_value" not in body["columns"]


def test_intro_question_does_not_query_default_gmv() -> None:
    response = client.post("/api/chat", json={"question": "你是谁？"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is False
    assert body["rows"] == []
    assert body["sql_source"] == "not_applicable"
    assert "DB Sentinel Agent" in body["answer"]
    assert "GMV 最高" not in body["answer"]


def test_greeting_question_does_not_query_default_gmv() -> None:
    response = client.post("/api/chat", json={"question": "你好"})
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert body["sql"] == "无需执行 SQL"
    assert "可审计的数据分析 Agent Demo" in body["answer"]


def test_out_of_scope_question_does_not_query_default_gmv_without_llm(monkeypatch) -> None:
    monkeypatch.setattr(agent_module, "ask_openai_compatible", lambda *args, **kwargs: None)
    response = client.post("/api/chat", json={"question": "晚上吃什么"})
    assert response.status_code == 200
    body = response.json()
    assert body["blocked"] is False
    assert body["rows"] == []
    assert body["sql_source"] == "not_applicable"
    assert body["sql"] == "无需执行 SQL"
    assert "不在当前 DB Sentinel Agent Demo 的数据分析范围内" in body["answer"]
    assert "GMV 最高" not in body["answer"]


def test_out_of_scope_question_uses_llm_boundary_answer_when_available(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_module,
        "ask_openai_compatible",
        lambda *args, **kwargs: "我是 DB Sentinel Agent，当前只能回答内置 Demo 数据分析问题。",
    )
    response = client.post("/api/chat", json={"question": "晚上吃什么"})
    assert response.status_code == 200
    body = response.json()
    assert body["rows"] == []
    assert body["generated_by"] == "llm"
    assert body["sql_source"] == "llm_boundary"
    assert body["answer"] == "我是 DB Sentinel Agent，当前只能回答内置 Demo 数据分析问题。"


def test_audit_contains_plan_sql_guard_and_execution() -> None:
    response = client.post("/api/chat", json={"question": "哪个渠道转化率下降最多，可能原因是什么？"})
    body = response.json()

    audit_response = client.get(f"/api/audit/{body['session_id']}")
    assert audit_response.status_code == 200
    kinds = [record["kind"] for record in audit_response.json()["records"]]
    assert "plan" in kinds
    assert "sql_generate" in kinds
    assert "guard" in kinds
    assert "execution" in kinds


def test_demo_reset_disabled_by_default() -> None:
    response = client.post("/api/demo/reset")
    assert response.status_code == 403
    assert response.json()["detail"] == "demo reset disabled"


def test_demo_reset_can_be_enabled_for_local_demo(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "DEMO_RESET_ENABLED", True)
    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    assert response.json()["status"] == "reset"
