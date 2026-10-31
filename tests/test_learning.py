from fastapi.testclient import TestClient
import micro_helper.api as api

client = TestClient(api.app)


def test_learning_plan_crud_and_versioning(tmp_path):
    api.DATABASE_PATH = tmp_path / "learning.sqlite3"
    created = client.post("/v1/learning/plans", json={
        "title": "Čeština", "objective": "Rozšířit slovní zásobu",
        "status": "active", "steps": ["Importovat slovník"], "sources": ["user://slovnik.csv"]
    })
    assert created.status_code == 201
    plan = created.json()
    assert plan["version"] == 1
    assert client.get("/v1/learning/plans").json()["plans"][0]["id"] == plan["id"]
    updated = client.put(f"/v1/learning/plans/{plan['id']}", json={
        "title": "Čeština 2", "objective": "Procvičit slovní zásobu",
        "status": "paused", "steps": ["Import", "Test"], "sources": []
    })
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["status"] == "paused"
    assert client.delete(f"/v1/learning/plans/{plan['id']}").json()["deleted"] is True
    assert client.get(f"/v1/learning/plans/{plan['id']}").status_code == 404


def test_learning_plan_validation(tmp_path):
    api.DATABASE_PATH = tmp_path / "learning-validation.sqlite3"
    assert client.post("/v1/learning/plans", json={
        "title": "", "objective": "x"
    }).status_code == 422
