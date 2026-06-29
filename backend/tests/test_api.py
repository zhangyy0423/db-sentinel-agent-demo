from __future__ import annotations

from fastapi.testclient import TestClient

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
