import secrets
import os
import json
import base64
from datetime import datetime, timedelta
import hashlib
from . import database

try:
    import pyotp
except ImportError:
    pyotp = None

try:
    import argon2
except ImportError:
    argon2 = None

class OmniAuthManager:
    def __init__(self):
        database.init_db()
        if argon2:
            self.ph = argon2.PasswordHasher()
        else:
            self.ph = None

    def generate_secure_token(self, length=32):
        return secrets.token_urlsafe(length)

    def generate_totp_secret(self):
        if pyotp:
            return pyotp.random_base32()
        return secrets.token_hex(16).upper() # Fallback if pyotp is missing

    def register_user_with_token(self, username, role="operator", days_valid=30, enable_mfa=False, metadata=None, password=None):
        """
        Creates a user (if not exists) and generates/registers a new token for them.
        If password is provided, it updates the user's password_hash.
        """
        user_info = database.get_user(username=username)
        if not user_info:
            user_uuid = database.create_user(username, metadata=json.dumps(metadata) if metadata else None)
            user_info = database.get_user(user_uuid=user_uuid)
        else:
            user_uuid = user_info["uuid"]

        if password:
            pwd_hash = self._hash_password(password)
            database.update_user_password(user_uuid, pwd_hash)

        # Ensure role is persisted in users table
        database.update_user(user_uuid, role=role)

        if enable_mfa and not user_info["mfa_enabled"]:
            totp_secret = self.generate_totp_secret()
            database.update_user_mfa(user_uuid, totp_secret, enabled=1)
            user_info = database.get_user(user_uuid=user_uuid)

        # Generate tokens using the new helper
        token_data = self._generate_tokens(user_uuid, username, role, days_valid=days_valid)

        # Phase 14: Terminal Confirmation for sensitive roles
        if role in ["admin", "operator"]:
            print(f"\n[omni_auth] 🛡️ SENSITIVE USER CREATED: {username} ({role})")
            print(f"[omni_auth] | Token: {token_data['token']}")
            print(f"[omni_auth] | Refresh: {token_data['refresh_token']}")
            print("[omni_auth] | PLEASE VISUALLY CONFIRM OR SECURE COPIES NOW.\n")
            
        return token_data

    def _generate_tokens(self, user_uuid, username, role, days_valid=30):
        """Genera par de tokens (access + refresh) para un usuario."""
        token = self.generate_secure_token()
        database.create_token(user_uuid, token, role=role, days_valid=days_valid)
        refresh_token = self.generate_secure_token(length=64)
        database.create_refresh_token(user_uuid, refresh_token)
        user_info = database.get_user(user_uuid=user_uuid)
        return {
            "token": token,
            "refresh_token": refresh_token,
            "uuid": user_uuid,
            "username": username,
            "role": role,
            "mfa_enabled": bool(user_info["mfa_enabled"]),
            "totp_secret": user_info["totp_secret"] if user_info["mfa_enabled"] else None,
            "expires_in_days": days_valid
        }

    def verify_token(self, token):
        """
        Validates a token against the database.
        Returns the token info if valid, None otherwise.
        """
        # Feature: Support a 'Master Token' from environment for emergency/dev access
        master_token = os.getenv("OMNI_MASTER_TOKEN")
        if master_token and token == master_token:
            return {
                "token": token,
                "user_uuid": "00000000-0000-0000-0000-000000000000",
                "username": "system-admin",
                "role": "admin",
                "status": "active",
                "is_elevated": True # Master token is always elevated
            }
            
        token_info = database.validate_token(token)
        if token_info:
            # Check if session is currently elevated
            elevated = False
            if token_info["elevation_expires_at"]:
                expiry = datetime.fromisoformat(token_info["elevation_expires_at"])
                if expiry > datetime.now():
                    elevated = True
            
            # Explicitly cast to dict and add elevation status
            res = dict(token_info)
            res["is_elevated"] = elevated
            return res
            
        return None

    def verify_totp(self, user_uuid, otp):
        if not pyotp:
            # If pyotp is missing but MFA is enabled, we can't verify.
            # In a real scenario, this should be a critical error.
            return False
            
        user_info = database.get_user(user_uuid=user_uuid)
        if not user_info or not user_info["mfa_enabled"] or not user_info["totp_secret"]:
            return False
            
        totp = pyotp.TOTP(user_info["totp_secret"])
        return totp.verify(otp)

    def elevate_session(self, token, otp, window_minutes=30):
        token_info = self.verify_token(token)
        if not token_info:
            return False
            
        if self.verify_totp(token_info["user_uuid"], otp):
            expiry = datetime.now() + timedelta(minutes=window_minutes)
            database.update_elevation(token, expiry)
            return True
        return False

    def _hash_password(self, password):
        if self.ph:
            return self.ph.hash(password)
            
        # Fallback to PBKDF2 if argon2 is missing
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        )
        return base64.b64encode(salt + pwd_hash).decode('utf-8')

    def _verify_password(self, password, stored_hash):
        if not stored_hash:
            return False, False
            
        # Try Argon2 first
        if self.ph:
            try:
                if self.ph.verify(stored_hash, password):
                    # Check if it needs re-hashing (parameters changed)
                    return True, self.ph.check_needs_rehash(stored_hash)
            except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError):
                pass # Fall through to PBKDF2 check
            except Exception:
                pass # Not an Argon2 hash
        
        # Fallback to PBKDF2 check
        try:
            decoded: bytes = base64.b64decode(stored_hash)
            if len(decoded) < 16:
                return False, False
            salt: bytes = decoded[:16]
            expected: bytes = decoded[16:]
            actual = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                100000
            )
            if secrets.compare_digest(actual, expected):
                return True, True # Successful PBKDF2 login always needs re-hash to Argon2
        except Exception:
            pass
            
        return False, False

    def login(self, username, password):
        """Authenticates with password and returns tokens."""
        user_info = database.get_user(username=username)
        if not user_info or not user_info["password_hash"]:
            self.log_action(None, username, "login_failed", "User not found or no password set")
            return None
            
        if not user_info.get("is_active", 1):
            self.log_action(user_info["uuid"], username, "login_failed", "User inactive")
            return None

        is_valid, needs_rehash = self._verify_password(password, user_info["password_hash"])
        
        if is_valid:
            if needs_rehash:
                new_hash = self._hash_password(password)
                database.update_user_password(user_info["uuid"], new_hash)
                
            role = user_info.get("role", "operator")
            token_data = self._generate_tokens(user_uuid=user_info["uuid"], username=username, role=role)
            self.log_action(user_info["uuid"], username, "login_success")
            return token_data
        
        self.log_action(user_info["uuid"], username, "login_failed", "Invalid password")
        return None

    def refresh_session(self, refresh_token, days_valid=30):
        """
        Uses a refresh token to generate a new short-lived access token.
        """
        refresh_info = database.validate_refresh_token(refresh_token)
        if not refresh_info:
            return None
            
        user_info = database.get_user(user_uuid=refresh_info["user_uuid"])
        if not user_info or not user_info.get("is_active", 1):
            return None

        role = user_info.get("role", "operator")
        return self._generate_tokens(user_uuid=user_info["uuid"], username=user_info["username"], role=role, days_valid=days_valid)

    def revoke_token(self, token):
        database.revoke_token(token)
        
    def revoke_refresh_token(self, token):
        database.revoke_refresh_token(token)

    def log_action(self, user_uuid, username, action, detail=None, ip_address=None):
        """Registra una acción en el audit log."""
        database.insert_audit_log(user_uuid, username, action, detail, ip_address)
