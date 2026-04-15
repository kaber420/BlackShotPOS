import sqlite3
import os
import uuid
import hashlib
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "omni_auth.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            uuid TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            totp_secret TEXT,
            mfa_enabled INTEGER DEFAULT 0,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Ensure password_hash exists in existing databases
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # v2 Migrations: role and is_active
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'operator'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    
    # Tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,
            role TEXT DEFAULT 'operator',
            status TEXT DEFAULT 'active',
            elevation_expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_uuid) REFERENCES users (uuid)
        )
    """)

    # Refresh tokens table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token TEXT PRIMARY KEY,
            user_uuid TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_uuid) REFERENCES users (uuid)
        )
    """)

    # WebAuthn credentials table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_uuid TEXT NOT NULL,
            credential_id TEXT NOT NULL,
            public_key TEXT NOT NULL,
            sign_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_uuid) REFERENCES users (uuid)
        )
    """)

    # Audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_uuid TEXT,
            username TEXT,
            action TEXT NOT NULL,
            detail TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def get_user(user_uuid=None, username=None):
    conn = get_connection()
    cursor = conn.cursor()
    if user_uuid:
        cursor.execute("SELECT * FROM users WHERE uuid = ?", (user_uuid,))
    else:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_user_mfa(user_uuid, totp_secret, enabled=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET totp_secret = ?, mfa_enabled = ? WHERE uuid = ?",
        (totp_secret, enabled, user_uuid)
    )
    conn.commit()
    conn.close()

def update_elevation(token, expires_at):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    cursor.execute(
        "UPDATE tokens SET elevation_expires_at = ? WHERE token = ?",
        (expires_at.isoformat() if expires_at else None, hashed_token)
    )
    conn.commit()
    conn.close()

def update_user_password(user_uuid, password_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE uuid = ?",
        (password_hash, user_uuid)
    )
    conn.commit()
    conn.close()

def list_users(include_inactive=False):
    conn = get_connection()
    cursor = conn.cursor()
    if include_inactive:
        cursor.execute("SELECT uuid, username, role, is_active, mfa_enabled, created_at FROM users")
    else:
        cursor.execute("SELECT uuid, username, role, is_active, mfa_enabled, created_at FROM users WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_user(user_uuid, username=None, role=None, is_active=None):
    conn = get_connection()
    cursor = conn.cursor()
    updates = []
    params = []
    if username is not None:
        updates.append("username = ?")
        params.append(username)
    if role is not None:
        updates.append("role = ?")
        params.append(role)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)
    if not updates:
        conn.close()
        return False
    params.append(user_uuid)
    cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE uuid = ?", params)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def create_user(username, metadata=None):
    user_uuid = str(uuid.uuid4())
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (uuid, username, metadata) VALUES (?, ?, ?)",
            (user_uuid, username, metadata)
        )
        conn.commit()
        return user_uuid
    except sqlite3.IntegrityError:
        # User already exists, return existing uuid
        cursor.execute("SELECT uuid FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return row["uuid"] if row else None
    finally:
        conn.close()

def _hash_token(token):
    """Auxiliary function to hash a token string for safe storage."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def create_token(user_uuid, token, role="operator", days_valid=30):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    expires_at = datetime.now() + timedelta(days=days_valid)
    cursor.execute(
        "INSERT INTO tokens (token, user_uuid, role, expires_at) VALUES (?, ?, ?, ?)",
        (hashed_token, user_uuid, role, expires_at.isoformat())
    )
    conn.commit()
    conn.close()

def validate_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    cursor.execute("""
        SELECT t.*, u.username 
        FROM tokens t
        JOIN users u ON t.user_uuid = u.uuid
        WHERE t.token = ? AND t.status = 'active' AND u.is_active = 1
    """, (hashed_token,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at > datetime.now():
            return dict(row)
    return None

def create_refresh_token(user_uuid, token, days_valid=90):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    expires_at = datetime.now() + timedelta(days=days_valid)
    cursor.execute(
        "INSERT INTO refresh_tokens (token, user_uuid, expires_at) VALUES (?, ?, ?)",
        (hashed_token, user_uuid, expires_at.isoformat())
    )
    conn.commit()
    conn.close()

def validate_refresh_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    cursor.execute("""
        SELECT r.*, u.username, u.uuid as user_uuid
        FROM refresh_tokens r
        JOIN users u ON r.user_uuid = u.uuid
        WHERE r.token = ?
    """, (hashed_token,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at > datetime.now():
            return dict(row)
    return None

def revoke_refresh_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    cursor.execute("DELETE FROM refresh_tokens WHERE token = ?", (hashed_token,))
    conn.commit()
    conn.close()

def revoke_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    hashed_token = _hash_token(token)
    cursor.execute("UPDATE tokens SET status = 'revoked' WHERE token = ?", (hashed_token,))
    conn.commit()
    conn.close()

def revoke_all_user_tokens(user_uuid):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tokens SET status = 'revoked' WHERE user_uuid = ?", (user_uuid,))
    cursor.execute("DELETE FROM refresh_tokens WHERE user_uuid = ?", (user_uuid,))
    conn.commit()
    conn.close()

def update_user_metadata(user_uuid: str, metadata_json: str) -> bool:
    """Actualiza el campo metadata (JSON) de un usuario."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET metadata = ? WHERE uuid = ?",
        (metadata_json, user_uuid)
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0

def insert_audit_log(user_uuid, username, action, detail=None, ip_address=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO audit_log (user_uuid, username, action, detail, ip_address) VALUES (?, ?, ?, ?, ?)",
        (user_uuid, username, action, detail, ip_address)
    )
    conn.commit()
    conn.close()

def get_audit_log(limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
