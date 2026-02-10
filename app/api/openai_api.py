from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import httpx
from typing import List
from ..core.config import settings
from ..core.database import get_db
from ..middleware.auth_middleware import get_current_user
from ..utils.logger import logger

router = APIRouter()


@router.get("/openai/llm", response_model=List[str])
async def get_llm_models(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """
    Fetch and return list of available OpenAI LLM models.

    Makes a call to OpenAI API to retrieve available models,
    sorts them by creation date (descending), and returns
    a list of model IDs.

    Returns:
        List[str]: List of model IDs sorted by creation date (newest first)
    """
    logger.info("Fetching LLM models from OpenAI API", user_id=user_id)

    # Get user's API key from their settings
    query = text("SELECT openai_api_key FROM user_setting WHERE user_id = :user_id")
    result = db.execute(query, {"user_id": int(user_id)}).first()

    if not result or not result.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OpenAI API key not configured. Please set your API key in Settings."
        )

    api_key = result.openai_api_key

    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        if settings.openai_project:
            headers["OpenAI-Project"] = settings.openai_project

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers=headers,
                timeout=30.0
            )

            response.raise_for_status()
            data = response.json()

            # Extract models from response
            models = data.get("data", [])

            # Sort by created field in descending order (newest first)
            sorted_models = sorted(models, key=lambda x: x.get("created", 0), reverse=True)

            # Extract model IDs and remove duplicates while preserving order
            model_ids = []
            seen = set()
            for model in sorted_models:
                model_id = model.get("id")
                if model_id and model_id not in seen:
                    seen.add(model_id)
                    model_ids.append(model_id)

            logger.info(f"Retrieved {len(model_ids)} LLM models from OpenAI")

            return model_ids

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching OpenAI models", status_code=e.response.status_code, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch models from OpenAI API: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error fetching OpenAI models", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to OpenAI API: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching OpenAI models", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )
