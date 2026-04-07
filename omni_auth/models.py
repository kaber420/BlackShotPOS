from pydantic import BaseModel, Field
from typing import Optional

# === Requests ===

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    role: str = "operator"
    password: Optional[str] = None
    enable_mfa: bool = False

class UserUpdateRequest(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChangeRequest(BaseModel):
    new_password: str = Field(..., min_length=6)

class ElevateRequest(BaseModel):
    otp: str

class RefreshRequest(BaseModel):
    refresh_token: str

class VaultEncryptRequest(BaseModel):
    plaintext: str

class VaultDecryptRequest(BaseModel):
    encrypted_data: str

# === Responses ===

class TokenResponse(BaseModel):
    token: str
    refresh_token: str
    uuid: str
    username: str
    role: str
    mfa_enabled: bool
    totp_secret: Optional[str] = None
    expires_in_days: int

class UserInfo(BaseModel):
    uuid: str
    username: str
    role: str
    is_active: bool
    mfa_enabled: bool
    created_at: str

class MessageResponse(BaseModel):
    status: str
    message: str
