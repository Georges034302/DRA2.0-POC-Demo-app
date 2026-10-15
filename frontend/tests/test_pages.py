import base64, pathlib, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from app import app

def test_auth_required(monkeypatch):
    monkeypatch.setenv("DEMO_USERNAME","demo")
    monkeypatch.setenv("DEMO_PASSWORD","testpass")
    assert app.test_client().get("/").status_code==401

def test_health_unavailable(monkeypatch):
    from unittest.mock import patch
    with patch("app.client",return_value=None):
        assert app.test_client().get("/health").status_code==503
