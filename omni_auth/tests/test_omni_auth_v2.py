import pytest
import os
import sqlite3
import hashlib
from datetime import datetime, timedelta
from omni_auth.manager import OmniAuthManager
from omni_auth import database

# Mock the database path for tests
TEST_DB = "/tmp/omni_auth_v2_test.db"

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

def test_argon2_hashing_basic(manager):
    """Verify that new passwords use Argon2 hashing."""
    username = "argon_user"
    password = "secret_password"
    
    manager.register_user_with_token(username, password=password)
    user = database.get_user(username=username)
    
    # Argon2 hashes typically start with $argon2id$
    assert user["password_hash"].startswith("$argon2id$")
    
    # Verify login works
    login_res = manager.login(username, password)
    assert login_res is not None

def test_pbkdf2_migration_to_argon2(manager):
    """Verify that old PBKDF2 hashes are migrated to Argon2 on successful login."""
    username = "legacy_user"
    password = "legacy_password"
    
    # Manually create a user with a PBKDF2 hash
    import base64
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    legacy_hash = base64.b64encode(salt + pwd_hash).decode('utf-8')
    
    user_uuid = database.create_user(username)
    database.update_user_password(user_uuid, legacy_hash)
    
    # Verify it is stored as PBKDF2
    user_before = database.get_user(username=username)
    assert not user_before["password_hash"].startswith("$argon2id$")
    
    # Login should trigger migration
    login_res = manager.login(username, password)
    assert login_res is not None
    
    # Verify it is now Argon2id
    user_after = database.get_user(username=username)
    assert user_after["password_hash"].startswith("$argon2id$")
    
    # Subsequent login with Argon2 should still work
    assert manager.login(username, password) is not None

def test_token_hashing_security(manager):
    """Verify that tokens are stored as hashes in the DB, not raw strings."""
    username = "token_user"
    res = manager.register_user_with_token(username)
    raw_token = res["token"]
    raw_refresh = res["refresh_token"]
    
    # Query database directly
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    
    # Check access tokens table
    cursor.execute("SELECT token FROM tokens WHERE user_uuid = ?", (res["uuid"],))
    stored_token = cursor.fetchone()[0]
    
    # The stored token should NOT be the raw token
    assert stored_token != raw_token
    # It should be the SHA-256 hash
    expected_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
    assert stored_token == expected_hash
    
    # Check refresh tokens table
    cursor.execute("SELECT token FROM refresh_tokens WHERE user_uuid = ?", (res["uuid"],))
    stored_refresh = cursor.fetchone()[0]
    assert stored_refresh != raw_refresh
    expected_refresh_hash = hashlib.sha256(raw_refresh.encode('utf-8')).hexdigest()
    assert stored_refresh == expected_refresh_hash
    
    conn.close()
    
    # Verify that validation still works with the raw token
    assert manager.verify_token(raw_token) is not None
    assert manager.refresh_session(raw_refresh) is not None

def test_token_invalidation_after_hashing_migration(manager):
    """Verify that tokens stored as raw text (pre-migration) are invalid after the change."""
    username = "old_session_user"
    user_uuid = database.create_user(username)
    raw_token = "raw_token_from_v1"
    
    # Manually insert a raw token (simulating v1 state)
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tokens (token, user_uuid, expires_at) VALUES (?, ?, ?)",
        (raw_token, user_uuid, (datetime.now() + timedelta(days=1)).isoformat())
    )
    conn.commit()
    conn.close()
    
    # manager.verify_token should now fail because it expects a hash of the input in the DB
    # but the DB has the raw string "raw_token_from_v1" (which isn't a hash of itself)
    assert manager.verify_token(raw_token) is None
