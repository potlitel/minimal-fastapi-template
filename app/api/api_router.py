from typing import Optional
from fastapi import APIRouter
from app.api import api_messages
from app.api.endpoints import auth, users
from app.core.crud_utils import crud_router_factory
# from app.core import BaseRepository
from app.core.repositories import BaseRepository, UserRepository
from app.models import Base, User
from app.schemas.requests import UserCreateRequest
from app.schemas.responses import UserResponse

auth_router = APIRouter()
auth_router.include_router(auth.router, prefix="/auth", tags=["Auth"])

api_router = APIRouter(
    responses={
        401: {
            "description": "No `Authorization` access token header, token is invalid or user removed",
            "content": {
                "application/json": {
                    "examples": {
                        "not authenticated": {
                            "summary": "No authorization token header",
                            "value": {"detail": "Not authenticated"},
                        },
                        "invalid token": {
                            "summary": "Token validation failed, decode failed, it may be expired or malformed",
                            "value": {"detail": "Token invalid: {detailed error msg}"},
                        },
                        "removed user": {
                            "summary": api_messages.JWT_ERROR_USER_REMOVED,
                            "value": {"detail": api_messages.JWT_ERROR_USER_REMOVED},
                        },
                    }
                }
            },
        },
    }
)
api_router.include_router(users.router, prefix="/profile", tags=["Profile"])


    
# Se instancian los repositorios para cada modelo de la BD
user_repository = UserRepository(User)
users_router = crud_router_factory(user_repository, UserResponse, UserCreateRequest, "Users")
user_router = APIRouter()
user_router.include_router(users_router)
