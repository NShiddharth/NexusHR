import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .common_models import TokenPayload, UserRole

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-employee-management-key-2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hrs

security_scheme = HTTPBearer(auto_error=False)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except (jwt.InvalidTokenError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}"
        )

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> TokenPayload:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required"
        )
    return decode_access_token(credentials.credentials)

def require_roles(allowed_roles: List[Any]):
    # Normalize string role list
    normalized_allowed = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
    # Also support DEPT_MANAGER / DEPARTMENT_MANAGER alias
    if "DEPT_MANAGER" in normalized_allowed and "DEPARTMENT_MANAGER" not in normalized_allowed:
        normalized_allowed.append("DEPARTMENT_MANAGER")
    if "DEPARTMENT_MANAGER" in normalized_allowed and "DEPT_MANAGER" not in normalized_allowed:
        normalized_allowed.append("DEPT_MANAGER")

    def role_checker(user: TokenPayload = Security(get_current_user)):
        user_role = str(user.role).upper()
        if user_role not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of {normalized_allowed}, user has '{user_role}'"
            )
        return user
    return role_checker
