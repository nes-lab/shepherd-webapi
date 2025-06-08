import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import EmailStr
from pydantic import validate_call
from shepherd_core import local_now

from shepherd_server.api_user.utils_mail import mail_engine

from .api_experiment.models import WebExperiment
from .api_user.models import PasswordStr
from .api_user.models import User
from .api_user.utils_misc import calculate_hash
from .api_user.utils_misc import calculate_password_hash
from .config import CFG
from .logger import log


async def db_client() -> AgnosticDatabase:
    """Call this from within your event loop to get beanie setup."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    # Note: if ".shp" does not exist, it will be created
    await init_beanie(database=client.shp, document_models=[User, WebExperiment])
    return client.shp


def db_available(timeout: float = 2) -> bool:
    try:
        asyncio.run(asyncio.wait_for(db_client(), timeout=timeout))
    except asyncio.TimeoutError:
        log.error("Timed out waiting for database connection (%.2f s).", timeout)
        return False
    return True


@asynccontextmanager
async def db_context(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize application services."""
    app.db = await db_client()
    log.info("FastAPI DB-Client connected")
    yield
    log.info("DB-Client shut down")


@validate_call
async def db_create_admin(email: EmailStr, password: PasswordStr) -> None:
    await db_client()

    user = await User.by_email(email)
    if user is not None:
        log.error("User with that email already exists")
        return
    token_verification = calculate_hash(email + str(local_now()))[-12:]
    await mail_engine().send_verification_email(email, token_verification)
    admin = User(
        email=email,
        password_hash=calculate_password_hash(password),
        role="admin",
        group_confirmed_at=local_now(),
        token_verification=token_verification,
        disabled=CFG.mail_enabled,
        email_confirmed_at=None if CFG.mail_enabled else local_now(),
    )
    await User.insert_one(admin)
    log.info("Admin user added to DB")
