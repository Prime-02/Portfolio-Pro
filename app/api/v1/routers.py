from fastapi import APIRouter
from .endpoints import auth
from .endpoints import settings
from .endpoints import skills
from .endpoints import socials
from .endpoints import cert

router = APIRouter()
router.include_router(auth.router)
router.include_router(settings.router)
router.include_router(skills.router)
router.include_router(socials.router)
router.include_router(cert.router)
