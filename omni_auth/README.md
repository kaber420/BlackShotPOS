# 🛡️ OmniAuth v2: Hardened Security Module

OmniAuth is a generic, reusable, and production-ready authentication module for FastAPI. It provides state-of-the-art security, identity management, MFA, and audit logging.

## 🚀 Key Features (v2 Hardened)

- **Argon2id Password Hashing**: Uses the current industry-standard hashing (via `argon2-cffi`) for maximum resistance against cracking.
- **Token Hashing**: Access and Refresh tokens are stored only as SHA-256 hashes in the database. Compromising the database does not reveal active session tokens.
- **Legacy Migration**: Automatic, seamless re-hashing of legacy PBKDF2 passwords upon their next successful login.
- **Administrative CRUD**: Complete User management (List, Get, Update, Deactivate, Password Change) with built-in RBAC.
- **Audit Logging**: Comprehensive logging of critical security events (login, elevation, revocation).
- **MFA (TOTP)**: Built-in support for time-based passwords with session elevation.
- **Zero-Conf persistence**: Self-managed SQLite database (`omni_auth.db`).

## 🛠️ Quick Start (FastAPI)

1. **Copy the Folder**: Place the `omni_auth/` directory in your project.
2. **Install Dependencies**: 
   ```bash
   pip install fastapi uvicorn pyjwt pyotp argon2-cffi cryptography python-dotenv
   ```
3. **Include Router**:
   ```python
   from fastapi import FastAPI, Depends
   from omni_auth.api import router as auth_router
   from omni_auth.security import verify_omni_token, require_role

   app = FastAPI(title="My Secure App")
   app.include_router(auth_router)

   @app.get("/admin-only", dependencies=[Depends(require_role("admin"))])
   async def admin_data():
       return {"msg": "Welcome, Admin!"}
   ```

## 📋 API Endpoints

### Authentication & Sessions
- `POST /_auth/login`: Login with username/password. Returns tokens.
- `POST /_auth/refresh`: Refresh an access token using a refresh token.
- `POST /_auth/logout`: Revoke the current session token.
- `POST /_auth/logout-all`: Revoke all active sessions for the current user.
- `POST /_auth/elevate`: Elevate a session (MFA) to perform sensitive actions.

### User Management (Admin Only)
- `GET /_auth/users`: List all users.
- `GET /_auth/users/{uuid}`: Get detailed user profile.
- `PUT /_auth/users/{uuid}`: Update user info (role, status, username).
- `DELETE /_auth/users/{uuid}`: Deactivate a user and revoke all sessions.
- `PUT /_auth/users/{uuid}/password`: Administrative password reset.

### Identity & Utility
- `GET /_auth/me`: Get profile of the currently logged-in user.
- `GET /_auth/audit`: (Admin Only) View the system audit log.
- `POST /_auth/vault/encrypt`: Per-user secure vault storage.

## 🧪 Testing
The module includes a comprehensive security verification suite:
```bash
PYTHONPATH=. pytest omni_auth/tests/ -v
```

## ⚙️ Configuration
- `OMNI_MASTER_TOKEN`: Emergency/dev access token.
- `OMNIVAULT_SEED`: Master secret for vault encryption.
- `OMNI_AUTH_METHODS`: Comma-separated list of enabled methods (default: `token,password`).
