import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from omni_auth.manager import OmniAuthManager
from omni_auth import database

# Mock the database path for tests
TEST_DB = "/tmp/omni_auth_test.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup a clean database for each test."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Patch the DB_PATH in the database module
    monkeypatch.setattr(database, "DB_PATH", TEST_DB)
    database.init_db()
    
    yield
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

@pytest.fixture
def manager():
    return OmniAuthManager()

def test_register_and_login_keeps_role(manager):
    """Verifica que un usuario mantiene su rol después de login."""
    username = "admin_user"
    password = "admin_password"
    role = "admin"
    
    # Registrar
    res = manager.register_user_with_token(username, role=role, password=password)
    assert res["role"] == role
    
    # Login
    login_res = manager.login(username, password)
    assert login_res is not None
    assert login_res["role"] == role
    assert login_res["username"] == username

def test_refresh_keeps_role(manager):
    """Verifica que el refresh token mantiene el rol del usuario."""
    res = manager.register_user_with_token("operator_user", role="operator")
    refresh_token = res["refresh_token"]
    
    refresh_res = manager.refresh_session(refresh_token)
    assert refresh_res is not None
    assert refresh_res["role"] == "operator"

def test_inactive_user_cannot_login(manager):
    """Verifica que un usuario desactivado no puede iniciar sesión."""
    username = "fired_user"
    password = "password"
    res = manager.register_user_with_token(username, role="operator", password=password)
    user_uuid = res["uuid"]
    
    # Desactivar usuario
    database.update_user(user_uuid, is_active=0)
    
    # Intentar login
    assert manager.login(username, password) is None
    
    # Intentar refresh
    assert manager.refresh_session(res["refresh_token"]) is None

def test_revoke_token_works(manager):
    """Verifica que la revocación de tokens individuales funciona."""
    res = manager.register_user_with_token("temp_user", role="operator")
    token = res["token"]
    
    assert manager.verify_token(token) is not None
    
    manager.revoke_token(token)
    assert manager.verify_token(token) is None

def test_revoke_all_user_tokens(manager):
    """Verifica que la revocación de todas las sesiones de un usuario funciona."""
    username = "multi_session_user"
    res1 = manager.register_user_with_token(username, password="password")
    res2 = manager.login(username, "password") # Register above created user
    
    user_uuid = res1["uuid"]
    
    database.revoke_all_user_tokens(user_uuid)
    
    assert manager.verify_token(res1["token"]) is None
    assert manager.verify_token(res2["token"]) is None
    assert manager.refresh_session(res1["refresh_token"]) is None

def test_audit_log_entries(manager):
    """Verifica que las acciones críticas se registran en el audit log."""
    username = "audit_user"
    password = "password"
    
    manager.register_user_with_token(username, password=password)
    manager.login(username, password)
    manager.login(username, "wrong_password")
    
    logs = database.get_audit_log(limit=10)
    actions = [log["action"] for log in logs]
    
    assert "login_success" in actions
    assert "login_failed" in actions

def test_pydantic_models_import():
    """Verifica que los modelos se pueden importar y usar."""
    from omni_auth.models import LoginRequest
    r = LoginRequest(username="test", password="password")
    assert r.username == "test"
