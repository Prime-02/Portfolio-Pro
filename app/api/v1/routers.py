from fastapi import APIRouter
from .endpoints import auth
from .endpoints import settings
from .endpoints import skills
from .endpoints import socials
from .endpoints import cert
from .endpoints import projects
from .endpoints import portfolioprojectassociation
from .endpoints import portfolio
from .endpoints import projectaudit
from .endpoints import notification
from .endpoints import projectengagements
from .endpoints import education
from .endpoints import contentblock
from .endpoints import testimonial

router = APIRouter()
router.include_router(auth.router)
router.include_router(settings.router)
router.include_router(skills.router)
router.include_router(socials.router)
router.include_router(cert.router)
router.include_router(projects.router)
router.include_router(portfolioprojectassociation.router)
router.include_router(portfolio.router)
router.include_router(projectaudit.router)
router.include_router(notification.router)
router.include_router(projectengagements.router)
router.include_router(education.router)
router.include_router(contentblock.router)
router.include_router(testimonial.rou)
