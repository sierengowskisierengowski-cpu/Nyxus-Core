from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import auth, config

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    expiresAt: float


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    if not auth.authenticate(body.username, body.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token, expiry = auth.create_session()
    return {"token": token, "username": config.AUTH_USERNAME, "expiresAt": expiry}


@router.post("/logout", status_code=204)
async def logout(token: str = Depends(auth.require_auth)):
    auth.revoke_session(token)


@router.get("/status")
async def status(token: str = Depends(auth.require_auth)):
    """Cheap endpoint the frontend uses to confirm a stored token is still valid."""
    return {"authenticated": True, "username": config.AUTH_USERNAME}
