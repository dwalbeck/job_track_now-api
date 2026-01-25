from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from ..core.database import get_db
from ..schemas.oauth import AuthorizeRequest, LoginRequest, TokenRequest, TokenResponse
from ..utils.oauth_utils import (
    generate_authorization_code,
    store_authorization_code,
    retrieve_authorization_code,
    mark_authorization_code_used,
    verify_pkce_challenge,
    create_access_token
)
from ..utils.logger import logger
from ..utils.password import verify_password


router = APIRouter()


@router.get("/authorize", response_class=HTMLResponse)
async def authorize(
    response_type: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str,
    client_id: Optional[str] = "",
    scope: Optional[str] = "all"
):
    """
    OAuth2 authorization endpoint - displays login form

    Args:
        response_type: Must be 'code' for authorization code flow
        redirect_uri: Callback URI where user will be redirected
        state: CSRF protection state token
        code_challenge: PKCE code challenge
        code_challenge_method: PKCE challenge method (S256)
        client_id: Optional client identifier
        scope: Requested scope

    Returns:
        HTML login form with embedded parameters
    """
    logger.info(f"Authorization request received",
                response_type=response_type,
                redirect_uri=redirect_uri,
                code_challenge_method=code_challenge_method)

    # Validate required parameters
    if response_type != "code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid response_type. Must be 'code'"
        )

    if code_challenge_method not in ["S256", "plain"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code_challenge_method. Must be 'S256' or 'plain'"
        )

    # Generate HTML login form with embedded parameters
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Job Track Now - Login</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}

            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                padding: 20px;
            }}

            .login-container {{
                background: white;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                max-width: 400px;
                width: 100%;
            }}

            h1 {{
                font-size: 2rem;
                font-weight: 700;
                color: #333;
                margin-bottom: 8px;
                text-align: center;
            }}

            .subtitle {{
                font-size: 1rem;
                color: #666;
                text-align: center;
                margin-bottom: 32px;
            }}

            .form-group {{
                margin-bottom: 20px;
            }}

            label {{
                display: block;
                font-size: 0.9rem;
                font-weight: 600;
                color: #333;
                margin-bottom: 8px;
            }}

            input[type="text"],
            input[type="password"] {{
                width: 100%;
                padding: 12px 16px;
                font-size: 1rem;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                transition: border-color 0.3s;
            }}

            input[type="text"]:focus,
            input[type="password"]:focus {{
                outline: none;
                border-color: #667eea;
            }}

            button {{
                width: 100%;
                padding: 14px 24px;
                font-size: 1rem;
                font-weight: 600;
                color: white;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
            }}

            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            }}

            button:active {{
                transform: translateY(0);
            }}

            .error-message {{
                background-color: #fee;
                color: #c33;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                font-size: 0.9rem;
                display: none;
            }}

            .info {{
                font-size: 0.85rem;
                color: #999;
                text-align: center;
                margin-top: 16px;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>Job Track Now</h1>
            <p class="subtitle">Sign in to continue</p>

            <div id="errorMessage" class="error-message"></div>

            <form id="loginForm" action="/v1/login" method="POST">
                <input type="hidden" name="response_type" value="{response_type}">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="scope" value="{scope}">
                <input type="hidden" name="state" value="{state}">
                <input type="hidden" name="code_challenge" value="{code_challenge}">
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">

                <div class="form-group">
                    <label for="username">Username</label>
                    <input
                        type="text"
                        id="username"
                        name="username"
                        required
                        autocomplete="username"
                        autofocus
                    >
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        required
                        autocomplete="current-password"
                    >
                </div>

                <button type="submit">Sign In</button>

                <p class="info">
                    Secure authentication using OAuth2 with PKCE
                </p>
            </form>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content, status_code=200)


@router.post("/login")
async def login(
    response_type: str = Form(...),
    redirect_uri: str = Form(...),
    state: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    client_id: Optional[str] = Form(""),
    scope: Optional[str] = Form("all"),
    db: Session = Depends(get_db)
):
    """
    OAuth2 login endpoint - authenticates user and generates authorization code

    Args:
        response_type: Must be 'code'
        redirect_uri: Callback URI
        state: CSRF state token
        code_challenge: PKCE code challenge
        code_challenge_method: PKCE challenge method
        username: User's username
        password: User's password
        client_id: Optional client identifier
        scope: Requested scope
        db: Database session

    Returns:
        Redirect to callback URI with authorization code
    """
    logger.info(f"Login attempt", username=username)

    # Authenticate user - users table
    try:
        first_name = None
        last_name = None
        authenticated = False
        is_admin = False

        # Try users table first (with hashed password)
        users_query = text("""
            SELECT user_id, login, passwd, first_name, last_name, is_admin
            FROM users
            WHERE login = :username
            LIMIT 1
        """)
        users_result = db.execute(users_query, {"username": username}).first()

        if users_result:
            # Verify hashed password
            logger.debug(f"Attempting password verification",
                        username=username,
                        password_length=len(password),
                        hash_length=len(users_result.passwd) if users_result.passwd else 0,
                        hash_prefix=users_result.passwd[:20] if users_result.passwd else None)
            if verify_password(password, users_result.passwd):
                authenticated = True
                first_name = users_result.first_name
                last_name = users_result.last_name
                is_admin = users_result.is_admin
                logger.info(f"User authenticated via users table", username=username)
            else:
                logger.warning(f"Login failed - invalid password (users table)", username=username)

        if not authenticated:
            logger.warning(f"Login failed - user not found or invalid password", username=username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        logger.info(f"Login successful", username=username,
                   first_name=first_name, last_name=last_name)

        # Generate authorization code
        auth_code = generate_authorization_code()

        # Store authorization code with associated data
        store_authorization_code(
            code=auth_code,
            username=username,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            state=state,
            scope=scope,
            user_id=users_result.user_id,
            is_admin=is_admin
        )

        # Redirect to callback URI with authorization code
        redirect_url = f"{redirect_uri}?code={auth_code}&state={state}"
        logger.info(f"Redirecting to callback", redirect_uri=redirect_uri)

        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


@router.post("/token", response_model=TokenResponse)
async def token(
    grant_type: str = Form(...),
    code: str = Form(...),
    code_verifier: str = Form(...),
    redirect_uri: str = Form(...),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    OAuth2 token endpoint - exchanges authorization code for access token

    Args:
        grant_type: Must be 'authorization_code'
        code: Authorization code from login
        code_verifier: PKCE code verifier
        redirect_uri: Callback URI (must match original)
        client_id: Optional client identifier
        client_secret: Optional client secret

    Returns:
        TokenResponse with access_token and metadata
    """
    logger.info(f"Token exchange request", grant_type=grant_type)

    # Validate grant type
    if grant_type != "authorization_code":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid grant_type. Must be 'authorization_code'"
        )

    # Retrieve stored authorization code data
    code_data = retrieve_authorization_code(code)
    if not code_data:
        logger.warning(f"Invalid authorization code")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired authorization code"
        )

    # Verify redirect URI matches
    if code_data["redirect_uri"] != redirect_uri:
        logger.warning(f"Redirect URI mismatch",
                      expected=code_data["redirect_uri"],
                      received=redirect_uri)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect URI mismatch"
        )

    # Verify PKCE code verifier
    if not verify_pkce_challenge(
        code_verifier,
        code_data["code_challenge"],
        code_data["code_challenge_method"]
    ):
        logger.warning(f"PKCE verification failed")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code_verifier"
        )

    # Mark code as used to prevent reuse
    mark_authorization_code_used(code)

    # Generate access token
    username = code_data["username"]
    scope = code_data["scope"]
    user_id = code_data["user_id"]
    is_admin = code_data["is_admin"]
    first_name = code_data.get("first_name")
    last_name = code_data.get("last_name")

    # If first_name/last_name not in code_data, retrieve from users table
    if not first_name or not last_name:
        users_query = text("SELECT first_name, last_name FROM users WHERE user_id = :user_id")
        users_result = db.execute(users_query, {"user_id": user_id}).first()
        if users_result:
            first_name = users_result.first_name
            last_name = users_result.last_name
        else:
            logger.warning(f"Failed to retrieve users first and last name", user_id=user_id)

    access_token = create_access_token(username=username, scope=scope, user_id=user_id, is_admin=is_admin, first_name=first_name, last_name=last_name)

    logger.info(f"Token issued successfully", username=username)

    return TokenResponse(
        access_token=access_token,
        token_type="Bearer",
        expires_in=86400  # 24 hours
    )
