from fastapi import Security, HTTPException, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from .manager import OmniAuthManager
from typing import Optional, Union, List

API_KEY_NAME = "X-Omni-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

_auth_manager = OmniAuthManager()

async def verify_omni_token(
    request: Request,
    api_key: Optional[str] = Security(api_key_header)
):
    """
    Standardized FastAPI dependency to verify an Omni token or mTLS certificate.
    Returns user_info including role and elevation status.
    """
    # Phase 12: Zero Login (mTLS)
    # Check if proxy verified a client certificate
    ssl_verify = request.headers.get("X-SSL-Cert-Verify")
    if ssl_verify == "SUCCESS":
        subject_dn = request.headers.get("X-SSL-Cert-Subject-DN", "")
        # Link subject DN to a user (e.g., CN=username)
        username = "mTLS-User"
        if "CN=" in subject_dn:
            # More robust split to handle cases like /CN=admin or CN=admin,O=Omni
            parts = subject_dn.split("CN=")
            if len(parts) > 1:
                username = parts[1].split(",")[0].split("/")[0].strip()
        
        # Treat as fully elevated system admin/operator if certificate is trusted
        return {
            "token": "mtls",
            "user_uuid": f"mtls-{username}",
            "username": username,
            "role": "admin", # Default to admin for trusted hardware keys
            "status": "active",
            "is_elevated": True # mTLS is high trust
        }

    if not api_key:
        # Fallback to query parameter for SSE/WebSockets
        api_key = request.query_params.get("token")

    if not api_key:
        raise HTTPException(
            status_code=401, 
            detail="Authentication required. Please provide X-Omni-Token or a valid mTLS certificate."
        )
        
    user_info = _auth_manager.verify_token(api_key)
    if not user_info:
        raise HTTPException(
            status_code=403, 
            detail="Invalid or expired Omni-Token."
        )
        
    # Ensure the token string is included in the response for logout functionality
    if "token" not in user_info:
        user_info["token"] = api_key
        
    return user_info

async def require_elevation(user_info: dict = Depends(verify_omni_token)):
    """
    Dependency to require that the current session is elevated (MFA verified).
    Returns 403 with a specific detail if not elevated, allowing clients to trigger OTP flow.
    """
    if not user_info.get("is_elevated"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "elevation_required",
                "message": "This action requires high-security session elevation (MFA).",
                "user_uuid": user_info["user_uuid"]
            }
        )
    return user_info

def require_role(role: Union[str, List[str]]):
    """
    Role-based access control dependency.
    Accepts a single role string or a list of roles.
    Admin always has access.
    
    Usage:
        Depends(require_role("admin"))
        Depends(require_role(["admin", "cajero"]))
    """
    allowed_roles = [role] if isinstance(role, str) else role
    
    async def role_checker(user_info: dict = Depends(verify_omni_token)):
        user_role = user_info.get("role", "")
        if user_role != "admin" and user_role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Requiere rol {allowed_roles}. Tu rol actual: '{user_role}'."
            )
        return user_info
    return role_checker
