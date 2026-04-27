import jwt
from datetime import datetime, timezone
from typing import Optional, Dict
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

def validate_bridge_token(token: str, public_key: str) -> Dict:
    """
    Valida un token JWT firmado con RS256 usando la llave pública del negocio.
    """
    try:
        # Decodificar y validar el token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            issuer="blackshot-central"
        )
        
        # Validaciones adicionales si son necesarias (ej. sub coincide con esta sucursal)
        # Por ahora confiamos en la validación de PyJWT para exp, iat, iss.
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("Bridge token expirado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token del bridge ha expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Bridge token inválido: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token del bridge inválido: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Error inesperado validando bridge token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno validando la autenticación del bridge",
        )
