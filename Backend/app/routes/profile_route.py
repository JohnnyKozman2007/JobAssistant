from fastapi import APIRouter, Depends, HTTPException, status

from ...database.db_client import Supabase, get_db
from ..models import ProfileCreate, ProfileUpdate, ProfileResponse

router = APIRouter()


@router.post(
    "/{user_id}/profile",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user profile",
    tags=["profiles"],
)
async def create_profile(user_id: str, profile: ProfileCreate, db: Supabase = Depends(get_db)):
    try:
        # Verify user exists
        existing_user = db.get_user(user_id)
        if not existing_user.data or len(existing_user.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if profile already exists for this user
        existing_profile = db.get_profile_by_user(user_id)
        if existing_profile.data and len(existing_profile.data) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Profile already exists for this user",
            )

        data = {
            "user_id": user_id,
            **profile.dict(),
        }
        result = db.create_profile(data)

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create profile",
            )

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/{user_id}/profile",
    response_model=ProfileResponse,
    summary="Get user profile",
    tags=["profiles"],
)
async def get_profile(user_id: str, db: Supabase = Depends(get_db)):
    try:
        # Verify user exists
        existing_user = db.get_user(user_id)
        if not existing_user.data or len(existing_user.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        result = db.get_profile_by_user(user_id)

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found for this user",
            )

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.put(
    "/{user_id}/profile",
    response_model=ProfileResponse,
    summary="Update user profile",
    tags=["profiles"],
)
async def update_profile(
    user_id: str, profile: ProfileUpdate, db: Supabase = Depends(get_db)
):
    try:
        # Verify user exists
        existing_user = db.get_user(user_id)
        if not existing_user.data or len(existing_user.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get existing profile
        existing_profile = db.get_profile_by_user(user_id)
        if not existing_profile.data or len(existing_profile.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found for this user",
            )

        profile_id = existing_profile.data[0]["id"]

        # Only update fields that were provided
        data = profile.dict(exclude_unset=True)

        if not data:
            # If no fields to update, return existing profile
            return existing_profile.data[0]

        result = db.update_profile(profile_id, data)

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update profile",
            )

        return result.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.delete(
    "/{user_id}/profile",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user profile",
    tags=["profiles"],
)
async def delete_profile(user_id: str, db: Supabase = Depends(get_db)):
    try:
        # Verify user exists
        existing_user = db.get_user(user_id)
        if not existing_user.data or len(existing_user.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get existing profile
        existing_profile = db.get_profile_by_user(user_id)
        if not existing_profile.data or len(existing_profile.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found for this user",
            )

        profile_id = existing_profile.data[0]["id"]
        db.delete_profile(profile_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
