from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any

from ..core.database import get_db
from ..schemas.user import UserRequest, UserResponse
from ..schemas.user_setting import UserSettingRequest, UserSettingResponse
from ..utils.logger import logger
from ..utils.password import hash_password
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/user/empty")
async def check_users_empty(db: Session = Depends(get_db)):
    """
    Check if the users table is empty (no users exist).

    This endpoint is used during initial setup to determine if the
    Settings/User page should be accessible without authentication
    (to allow creating the first user).

    Returns:
        dict with 'empty' boolean - True if no users exist, False if users exist
    """
    logger.info("Checking if users table is empty")

    try:
        query = text("SELECT COUNT(user_id) as user_count FROM users")
        result = db.execute(query).first()
        user_count = result.user_count if result else 0

        is_empty = user_count == 0
        logger.info(f"Users table check complete", user_count=user_count, is_empty=is_empty)

        return {"empty": is_empty}

    except Exception as e:
        logger.error("Failed to check users table", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check users: {str(e)}"
        )


@router.get("/user/lookup", response_model=UserResponse)
async def get_user_by_username(
    username: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve user information by username (login).

    Args:
        username: The login username of the user to retrieve

    Returns:
        UserResponse with complete user data including address and details
    """
    logger.info("Looking up user by username", username=username)

    try:
        query = text("""
            SELECT
                u.user_id, u.first_name, u.last_name, u.email, u.login, u.passwd, u.is_admin,
                a.address_id, a.address_1, a.address_2, a.city, a.state, a.zip, a.country,
                ud.phone, ud.linkedin_url, ud.github_url, ud.website_url, ud.portfolio_url
            FROM users u
            LEFT JOIN user_address ua ON (u.user_id = ua.user_id AND ua.is_default = true)
            LEFT JOIN address a ON (ua.address_id = a.address_id)
            LEFT JOIN user_detail ud ON (u.user_id = ud.user_id)
            WHERE u.login = :username
        """)

        result = db.execute(query, {"username": username}).first()

        if not result:
            logger.warning("User not found by username", username=username)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with username {username} not found"
            )

        logger.info("User retrieved successfully by username", username=username, user_id=result.user_id)

        return UserResponse(
            user_id=result.user_id,
            first_name=result.first_name,
            last_name=result.last_name,
            email=result.email,
            login=result.login,
            passwd=result.passwd,
            phone=result.phone,
            linkedin_url=result.linkedin_url,
            github_url=result.github_url,
            website_url=result.website_url,
            portfolio_url=result.portfolio_url,
            address_id=result.address_id,
            address_1=result.address_1,
            address_2=result.address_2,
            city=result.city,
            state=result.state,
            zip=result.zip,
            country=result.country
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve user by username", error=str(e), username=username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}"
        )


@router.get("/user", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve user information by user_id.

    Args:
        user_id: The ID of the user to retrieve

    Returns:
        UserResponse with complete user data including address and details
    """
    logger.info("Retrieving user", user_id=user_id)

    try:
        query = text("""
            SELECT
                u.user_id, u.first_name, u.last_name, u.email, u.login, u.passwd, u.is_admin,
                a.address_id, a.address_1, a.address_2, a.city, a.state, a.zip, a.country,
                ud.phone, ud.linkedin_url, ud.github_url, ud.website_url, ud.portfolio_url
            FROM users u
            LEFT JOIN user_address ua ON (u.user_id = ua.user_id AND ua.is_default = true)
            LEFT JOIN address a ON (ua.address_id = a.address_id)
            LEFT JOIN user_detail ud ON (u.user_id = ud.user_id)
            WHERE u.user_id = :user_id
        """)

        result = db.execute(query, {"user_id": user_id}).first()

        if not result:
            logger.warning("User not found", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )

        logger.info("User retrieved successfully", user_id=user_id)

        return UserResponse(
            user_id=result.user_id,
            first_name=result.first_name,
            last_name=result.last_name,
            email=result.email,
            login=result.login,
            passwd=result.passwd,
            phone=result.phone,
            linkedin_url=result.linkedin_url,
            github_url=result.github_url,
            website_url=result.website_url,
            portfolio_url=result.portfolio_url,
            address_id=result.address_id,
            address_1=result.address_1,
            address_2=result.address_2,
            city=result.city,
            state=result.state,
            zip=result.zip,
            country=result.country
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve user", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user: {str(e)}"
        )


@router.post("/user", response_model=UserResponse)
async def create_or_update_user(
    user_data: UserRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new user or update an existing user.

    If user_id is provided, updates the existing user.
    If user_id is not provided, creates a new user.

    For new users, required fields: first_name, last_name, login, passwd, email
    For updates, all fields are optional.

    Address validation: If any address field is provided, all address fields
    except address_2 are required.
    """
    try:
        is_update = user_data.user_id is not None

        if is_update:
            return await _update_user(user_data, db)
        else:
            return await _create_user(user_data, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User operation failed", error=str(e))
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User operation failed: {str(e)}"
        )


async def _create_user(user_data: UserRequest, db: Session) -> UserResponse:
    """Create a new user with all related records."""
    logger.info("Creating new user", login=user_data.login)

    try:
        # Check if login already exists
        check_query = text("SELECT user_id FROM users WHERE login = :login")
        existing = db.execute(check_query, {"login": user_data.login}).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Login username already exists"
            )

        # Check if email already exists
        check_email = text("SELECT user_id FROM users WHERE email = :email")
        existing_email = db.execute(check_email, {"email": user_data.email}).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )

        # Hash the password
        hashed_password = hash_password(user_data.passwd)

        # 1. Insert into users table
        insert_user = text("""
            INSERT INTO users (first_name, last_name, login, passwd, email)
            VALUES (:first_name, :last_name, :login, :passwd, :email)
            RETURNING user_id
        """)
        result = db.execute(insert_user, {
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "login": user_data.login,
            "passwd": hashed_password,
            "email": user_data.email
        })
        user_id = result.fetchone()[0]
        logger.info(f"Created user record", user_id=user_id)

        address_id = None

        # 2. Insert into address table (if address data provided)
        if _has_address_data(user_data):
            insert_address = text("""
                INSERT INTO address (address_1, address_2, city, state, zip, country)
                VALUES (:address_1, :address_2, :city, :state, :zip, :country)
                RETURNING address_id
            """)
            result = db.execute(insert_address, {
                "address_1": user_data.address_1,
                "address_2": user_data.address_2 or '',
                "city": user_data.city,
                "state": user_data.state,
                "zip": user_data.zip,
                "country": user_data.country or 'US'
            })
            address_id = result.fetchone()[0]
            logger.info(f"Created address record", address_id=address_id)

            # 3. Insert into user_address table
            insert_user_address = text("""
                INSERT INTO user_address (user_id, address_id, is_default, address_type)
                VALUES (:user_id, :address_id, TRUE, 'home')
            """)
            db.execute(insert_user_address, {
                "user_id": user_id,
                "address_id": address_id
            })
            logger.info(f"Created user_address link", user_id=user_id, address_id=address_id)

        # 4. Insert into user_detail table
        insert_detail = text("""
            INSERT INTO user_detail (user_id, phone, linkedin_url, github_url, website_url, portfolio_url)
            VALUES (:user_id, :phone, :linkedin_url, :github_url, :website_url, :portfolio_url)
        """)
        db.execute(insert_detail, {
            "user_id": user_id,
            "phone": user_data.phone or '',
            "linkedin_url": user_data.linkedin_url,
            "github_url": user_data.github_url,
            "website_url": user_data.website_url,
            "portfolio_url": user_data.portfolio_url
        })
        logger.info(f"Created user_detail record", user_id=user_id)

        db.commit()

        logger.info("User created successfully", user_id=user_id, login=user_data.login)

        return UserResponse(
            user_id=user_id,
            address_id=address_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            login=user_data.login,
            passwd=hashed_password,
            phone=user_data.phone,
            linkedin_url=user_data.linkedin_url,
            github_url=user_data.github_url,
            website_url=user_data.website_url,
            portfolio_url=user_data.portfolio_url,
            address_1=user_data.address_1,
            address_2=user_data.address_2,
            city=user_data.city,
            state=user_data.state,
            zip=user_data.zip,
            country=user_data.country
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create user", error=str(e))
        raise


async def _update_user(user_data: UserRequest, db: Session) -> UserResponse:
    """Update an existing user and related records."""
    user_id = user_data.user_id
    logger.info("Updating user", user_id=user_id)

    try:
        # Verify user exists
        check_query = text("SELECT user_id FROM users WHERE user_id = :user_id")
        existing = db.execute(check_query, {"user_id": user_id}).first()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )

        # 1. Update users table (only provided fields)
        user_updates = []
        user_params = {"user_id": user_id}

        if user_data.first_name:
            user_updates.append("first_name = :first_name")
            user_params["first_name"] = user_data.first_name
        if user_data.last_name:
            user_updates.append("last_name = :last_name")
            user_params["last_name"] = user_data.last_name
        if user_data.email:
            # Check if new email already exists for another user
            check_email = text("SELECT user_id FROM users WHERE email = :email AND user_id != :user_id")
            existing_email = db.execute(check_email, {"email": user_data.email, "user_id": user_id}).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists for another user"
                )
            user_updates.append("email = :email")
            user_params["email"] = user_data.email
        if user_data.login:
            # Check if new login already exists for another user
            check_login = text("SELECT user_id FROM users WHERE login = :login AND user_id != :user_id")
            existing_login = db.execute(check_login, {"login": user_data.login, "user_id": user_id}).first()
            if existing_login:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Login username already exists for another user"
                )
            user_updates.append("login = :login")
            user_params["login"] = user_data.login
        if user_data.passwd:
            hashed_password = hash_password(user_data.passwd)
            user_updates.append("passwd = :passwd")
            user_params["passwd"] = hashed_password

        if user_updates:
            update_user = text(f"UPDATE users SET {', '.join(user_updates)} WHERE user_id = :user_id")
            db.execute(update_user, user_params)
            logger.info(f"Updated users table", user_id=user_id)

        # 2. Update address table (if address data provided)
        address_id = user_data.address_id
        if _has_address_data(user_data):
            if address_id:
                # Update existing address
                update_address = text("""
                    UPDATE address
                    SET address_1 = :address_1, address_2 = :address_2, city = :city,
                        state = :state, zip = :zip, country = :country
                    WHERE address_id = :address_id
                """)
                db.execute(update_address, {
                    "address_id": address_id,
                    "address_1": user_data.address_1,
                    "address_2": user_data.address_2 or '',
                    "city": user_data.city,
                    "state": user_data.state,
                    "zip": user_data.zip,
                    "country": user_data.country or 'US'
                })
                logger.info(f"Updated address record", address_id=address_id)
            else:
                # Create new address and link
                insert_address = text("""
                    INSERT INTO address (address_1, address_2, city, state, zip, country)
                    VALUES (:address_1, :address_2, :city, :state, :zip, :country)
                    RETURNING address_id
                """)
                result = db.execute(insert_address, {
                    "address_1": user_data.address_1,
                    "address_2": user_data.address_2 or '',
                    "city": user_data.city,
                    "state": user_data.state,
                    "zip": user_data.zip,
                    "country": user_data.country or 'US'
                })
                address_id = result.fetchone()[0]
                logger.info(f"Created new address record", address_id=address_id)

                # Link to user
                insert_user_address = text("""
                    INSERT INTO user_address (user_id, address_id, is_default, address_type)
                    VALUES (:user_id, :address_id, TRUE, 'home')
                    ON CONFLICT (user_id, address_id) DO NOTHING
                """)
                db.execute(insert_user_address, {
                    "user_id": user_id,
                    "address_id": address_id
                })
                logger.info(f"Created user_address link", user_id=user_id, address_id=address_id)

        # 3. Update user_detail table
        detail_updates = []
        detail_params = {"user_id": user_id}

        if user_data.phone is not None:
            detail_updates.append("phone = :phone")
            detail_params["phone"] = user_data.phone or ''
        if user_data.linkedin_url is not None:
            detail_updates.append("linkedin_url = :linkedin_url")
            detail_params["linkedin_url"] = user_data.linkedin_url
        if user_data.github_url is not None:
            detail_updates.append("github_url = :github_url")
            detail_params["github_url"] = user_data.github_url
        if user_data.website_url is not None:
            detail_updates.append("website_url = :website_url")
            detail_params["website_url"] = user_data.website_url
        if user_data.portfolio_url is not None:
            detail_updates.append("portfolio_url = :portfolio_url")
            detail_params["portfolio_url"] = user_data.portfolio_url

        if detail_updates:
            # Check if user_detail exists
            check_detail = text("SELECT user_id FROM user_detail WHERE user_id = :user_id")
            detail_exists = db.execute(check_detail, {"user_id": user_id}).first()

            if detail_exists:
                update_detail = text(f"UPDATE user_detail SET {', '.join(detail_updates)} WHERE user_id = :user_id")
                db.execute(update_detail, detail_params)
            else:
                # Insert new detail record
                insert_detail = text("""
                    INSERT INTO user_detail (user_id, phone, linkedin_url, github_url, website_url, portfolio_url)
                    VALUES (:user_id, :phone, :linkedin_url, :github_url, :website_url, :portfolio_url)
                """)
                db.execute(insert_detail, {
                    "user_id": user_id,
                    "phone": user_data.phone or '',
                    "linkedin_url": user_data.linkedin_url,
                    "github_url": user_data.github_url,
                    "website_url": user_data.website_url,
                    "portfolio_url": user_data.portfolio_url
                })
            logger.info(f"Updated user_detail record", user_id=user_id)

        db.commit()

        # Fetch updated data for response
        return await _get_user_data(user_id, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user", error=str(e), user_id=user_id)
        raise


async def _get_user_data(user_id: int, db: Session) -> UserResponse:
    """Fetch complete user data for response."""
    query = text("""
        SELECT
            u.user_id, u.first_name, u.last_name, u.email, u.login, u.passwd,
            ud.phone, ud.linkedin_url, ud.github_url, ud.website_url, ud.portfolio_url,
            a.address_id, a.address_1, a.address_2, a.city, a.state, a.zip, a.country
        FROM users u
        LEFT JOIN user_detail ud ON u.user_id = ud.user_id
        LEFT JOIN user_address ua ON u.user_id = ua.user_id
        LEFT JOIN address a ON ua.address_id = a.address_id
        WHERE u.user_id = :user_id
    """)
    result = db.execute(query, {"user_id": user_id}).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )

    return UserResponse(
        user_id=result.user_id,
        first_name=result.first_name,
        last_name=result.last_name,
        email=result.email,
        login=result.login,
        passwd=result.passwd,
        phone=result.phone,
        linkedin_url=result.linkedin_url,
        github_url=result.github_url,
        website_url=result.website_url,
        portfolio_url=result.portfolio_url,
        address_id=result.address_id,
        address_1=result.address_1,
        address_2=result.address_2,
        city=result.city,
        state=result.state,
        zip=result.zip,
        country=result.country
    )


def _has_address_data(user_data: UserRequest) -> bool:
    """Check if any address field has a value."""
    address_fields = [
        user_data.address_1, user_data.address_2, user_data.city,
        user_data.state, user_data.zip, user_data.country
    ]
    return any(f and str(f).strip() for f in address_fields)


# ============================================================================
# User Setting Endpoints
# ============================================================================

@router.get("/user/setting", response_model=UserSettingResponse)
async def get_user_setting(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve user settings by user_id.

    Requires authentication. Users can only access their own settings.

    Args:
        user_id: The ID of the user whose settings to retrieve

    Returns:
        UserSettingResponse with all user settings
    """
    # Verify user can only access their own settings
    token_user_id = current_user.get("user_id")
    if token_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access settings for another user"
        )

    logger.info("Retrieving user settings", user_id=user_id)

    try:
        query = text("""
            SELECT user_id, no_response_week, docx2html, odt2html, pdf2html,
                   html2docx, html2odt, html2pdf, default_llm, resume_extract_llm,
                   job_extract_llm, rewrite_llm, cover_llm, company_llm, tools_llm,
                   openai_api_key, tinymce_api_key, convertapi_key
            FROM user_setting
            WHERE user_id = :user_id
        """)

        result = db.execute(query, {"user_id": user_id}).first()

        if not result:
            logger.warning("User settings not found", user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Settings for user_id {user_id} not found"
            )

        logger.info("User settings retrieved successfully", user_id=user_id)

        return UserSettingResponse(
            user_id=result.user_id,
            no_response_week=result.no_response_week,
            docx2html=result.docx2html,
            odt2html=result.odt2html,
            pdf2html=result.pdf2html,
            html2docx=result.html2docx,
            html2odt=result.html2odt,
            html2pdf=result.html2pdf,
            default_llm=result.default_llm,
            resume_extract_llm=result.resume_extract_llm,
            job_extract_llm=result.job_extract_llm,
            rewrite_llm=result.rewrite_llm,
            cover_llm=result.cover_llm,
            company_llm=result.company_llm,
            tools_llm=result.tools_llm,
            openai_api_key=result.openai_api_key,
            tinymce_api_key=result.tinymce_api_key,
            convertapi_key=result.convertapi_key
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve user settings", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user settings: {str(e)}"
        )


@router.post("/user/setting", response_model=UserSettingResponse)
async def create_or_update_user_setting(
    setting_data: UserSettingRequest,
    db: Session = Depends(get_db)
):
    """
    Create or update user settings.

    If settings exist for the user_id, updates them.
    If no settings exist, creates a new record.

    Args:
        setting_data: UserSettingRequest with settings data

    Returns:
        UserSettingResponse with the saved settings
    """
    user_id = setting_data.user_id
    logger.info("Creating/updating user settings", user_id=user_id)

    try:
        # Verify user exists
        check_user = text("SELECT user_id FROM users WHERE user_id = :user_id")
        user_exists = db.execute(check_user, {"user_id": user_id}).first()
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )

        # Check if settings already exist
        check_query = text("SELECT user_id FROM user_setting WHERE user_id = :user_id")
        existing = db.execute(check_query, {"user_id": user_id}).first()

        if existing:
            # Update existing settings
            update_fields = []
            params = {"user_id": user_id}

            if setting_data.no_response_week is not None:
                update_fields.append("no_response_week = :no_response_week")
                params["no_response_week"] = setting_data.no_response_week
            if setting_data.docx2html is not None:
                update_fields.append("docx2html = :docx2html")
                params["docx2html"] = setting_data.docx2html
            if setting_data.odt2html is not None:
                update_fields.append("odt2html = :odt2html")
                params["odt2html"] = setting_data.odt2html
            if setting_data.pdf2html is not None:
                update_fields.append("pdf2html = :pdf2html")
                params["pdf2html"] = setting_data.pdf2html
            if setting_data.html2docx is not None:
                update_fields.append("html2docx = :html2docx")
                params["html2docx"] = setting_data.html2docx
            if setting_data.html2odt is not None:
                update_fields.append("html2odt = :html2odt")
                params["html2odt"] = setting_data.html2odt
            if setting_data.html2pdf is not None:
                update_fields.append("html2pdf = :html2pdf")
                params["html2pdf"] = setting_data.html2pdf
            if setting_data.default_llm is not None:
                update_fields.append("default_llm = :default_llm")
                params["default_llm"] = setting_data.default_llm
            if setting_data.resume_extract_llm is not None:
                update_fields.append("resume_extract_llm = :resume_extract_llm")
                params["resume_extract_llm"] = setting_data.resume_extract_llm
            if setting_data.job_extract_llm is not None:
                update_fields.append("job_extract_llm = :job_extract_llm")
                params["job_extract_llm"] = setting_data.job_extract_llm
            if setting_data.rewrite_llm is not None:
                update_fields.append("rewrite_llm = :rewrite_llm")
                params["rewrite_llm"] = setting_data.rewrite_llm
            if setting_data.cover_llm is not None:
                update_fields.append("cover_llm = :cover_llm")
                params["cover_llm"] = setting_data.cover_llm
            if setting_data.company_llm is not None:
                update_fields.append("company_llm = :company_llm")
                params["company_llm"] = setting_data.company_llm
            if setting_data.tools_llm is not None:
                update_fields.append("tools_llm = :tools_llm")
                params["tools_llm"] = setting_data.tools_llm
            if setting_data.openai_api_key is not None:
                update_fields.append("openai_api_key = :openai_api_key")
                params["openai_api_key"] = setting_data.openai_api_key
            if setting_data.tinymce_api_key is not None:
                update_fields.append("tinymce_api_key = :tinymce_api_key")
                params["tinymce_api_key"] = setting_data.tinymce_api_key
            if setting_data.convertapi_key is not None:
                update_fields.append("convertapi_key = :convertapi_key")
                params["convertapi_key"] = setting_data.convertapi_key

            if update_fields:
                update_query = text(f"UPDATE user_setting SET {', '.join(update_fields)} WHERE user_id = :user_id")
                db.execute(update_query, params)
                logger.info("Updated user settings", user_id=user_id)

        else:
            # Insert new settings record
            insert_query = text("""
                INSERT INTO user_setting (
                    user_id, no_response_week, docx2html, odt2html, pdf2html,
                    html2docx, html2odt, html2pdf, default_llm, resume_extract_llm,
                    job_extract_llm, rewrite_llm, cover_llm, company_llm, tools_llm,
                    openai_api_key, tinymce_api_key, convertapi_key
                ) VALUES (
                    :user_id,
                    COALESCE(:no_response_week, 6),
                    COALESCE(:docx2html, 'docx-parser-converter'),
                    COALESCE(:odt2html, 'pandoc'),
                    COALESCE(:pdf2html, 'markitdown'),
                    COALESCE(:html2docx, 'html4docx'),
                    COALESCE(:html2odt, 'pandoc'),
                    COALESCE(:html2pdf, 'weasyprint'),
                    COALESCE(:default_llm, 'gpt-4o-mini'),
                    COALESCE(:resume_extract_llm, 'gpt-4.1-mini'),
                    COALESCE(:job_extract_llm, 'gpt-4.1-mini'),
                    COALESCE(:rewrite_llm, 'gpt-5.2'),
                    COALESCE(:cover_llm, 'gpt-4.1-mini'),
                    COALESCE(:company_llm, 'gpt-5.2'),
                    COALESCE(:tools_llm, 'gpt-4o-mini'),
                    :openai_api_key,
                    :tinymce_api_key,
                    :convertapi_key
                )
            """)
            db.execute(insert_query, {
                "user_id": user_id,
                "no_response_week": setting_data.no_response_week,
                "docx2html": setting_data.docx2html,
                "odt2html": setting_data.odt2html,
                "pdf2html": setting_data.pdf2html,
                "html2docx": setting_data.html2docx,
                "html2odt": setting_data.html2odt,
                "html2pdf": setting_data.html2pdf,
                "default_llm": setting_data.default_llm,
                "resume_extract_llm": setting_data.resume_extract_llm,
                "job_extract_llm": setting_data.job_extract_llm,
                "rewrite_llm": setting_data.rewrite_llm,
                "cover_llm": setting_data.cover_llm,
                "company_llm": setting_data.company_llm,
                "tools_llm": setting_data.tools_llm,
                "openai_api_key": setting_data.openai_api_key,
                "tinymce_api_key": setting_data.tinymce_api_key,
                "convertapi_key": setting_data.convertapi_key
            })
            logger.info("Created user settings", user_id=user_id)

        db.commit()

        # Fetch and return the saved settings
        return await get_user_setting(user_id, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to save user settings", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save user settings: {str(e)}"
        )
