"""API 集成测试"""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import init_db
from app.db.seed import seed_default_user
from app.core.config import config_loader

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup():
    """每次测试前初始化数据库"""
    config_loader._configs = {}
    config_loader.load_all()
    init_db()
    seed_default_user()
    yield


class TestAuthAPI:
    def test_health_check(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "ok"

    def test_login_success(self):
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert data["data"]["user"]["username"] == "admin"

    def test_login_failed(self):
        """免登录模式：任何密码都能登录成功"""
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "wrong",
        })
        # 免登录模式：始终返回成功
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    def test_unauthorized_access(self):
        """免登录模式：无需授权即可访问"""
        # 免登录模式下任何接口都可以直接访问
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


class TestSalaryRunAPI:
    _run_counter = 0

    def _auth_header(self) -> dict:
        resp = client.post("/api/v1/auth/login", json={
            "username": "admin", "password": "admin123",
        })
        token = resp.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_create_run(self):
        headers = self._auth_header()
        resp = client.post("/api/v1/salary-runs", json={
            "name": f"测试工资_{uuid.uuid4().hex[:4]}",
            "payroll_month": "2026-07",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["status"] == "CREATED"
        assert "测试工资" in data["data"]["name"]

    def test_list_runs(self):
        headers = self._auth_header()
        client.post("/api/v1/salary-runs", json={
            "name": f"列表测试_{uuid.uuid4().hex[:4]}", "payroll_month": "2026-07",
        }, headers=headers)

        resp = client.get("/api/v1/salary-runs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    def test_get_run_detail(self):
        headers = self._auth_header()
        create_resp = client.post("/api/v1/salary-runs", json={
            "name": f"详情测试_{uuid.uuid4().hex[:4]}", "payroll_month": "2026-07",
        }, headers=headers)
        run_id = create_resp.json()["data"]["id"]

        resp = client.get(f"/api/v1/salary-runs/{run_id}", headers=headers)
        assert resp.status_code == 200
        assert "详情测试" in resp.json()["data"]["name"]

    def test_duplicate_run_name(self):
        headers = self._auth_header()
        name = f"同名_{uuid.uuid4().hex[:4]}"
        client.post("/api/v1/salary-runs", json={
            "name": name, "payroll_month": "2026-07",
        }, headers=headers)
        resp = client.post("/api/v1/salary-runs", json={
            "name": name, "payroll_month": "2026-08",
        }, headers=headers)
        assert resp.status_code == 400
