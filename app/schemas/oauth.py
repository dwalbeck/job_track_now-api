from pydantic import BaseModel, Field
from typing import Optional


class AuthorizeRequest(BaseModel):
    """OAuth2 authorization request parameters"""
    response_type: str = Field(..., description="Must be 'code' for authorization code flow")
    client_id: Optional[str] = Field(None, description="Client identifier")
    redirect_uri: str = Field(..., description="Callback URI")
    scope: Optional[str] = Field("all", description="Requested scope")
    state: str = Field(..., description="CSRF protection state")
    code_challenge: str = Field(..., description="PKCE code challenge")
    code_challenge_method: str = Field(..., description="PKCE challenge method (S256)")


class LoginRequest(BaseModel):
    """OAuth2 login request with credentials"""
    response_type: str
    client_id: Optional[str] = None
    redirect_uri: str
    scope: Optional[str] = "all"
    state: str
    code_challenge: str
    code_challenge_method: str
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenRequest(BaseModel):
    """OAuth2 token exchange request"""
    grant_type: str = Field(..., description="Must be 'authorization_code'")
    code: str = Field(..., description="Authorization code")
    code_verifier: str = Field(..., description="PKCE code verifier")
    redirect_uri: str = Field(..., description="Callback URI")
    client_id: Optional[str] = None
    client_secret: Optional[str] = None


class TokenResponse(BaseModel):
    """OAuth2 token response"""
    access_token: str
    refresh_token: Optional[str] = None
    id_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = 86400  # 24 hours
