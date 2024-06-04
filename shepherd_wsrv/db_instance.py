from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.core import AgnosticDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from shepherd_core import local_now

from .api_experiment.models import ExperimentDB
from .api_user.models import User
from .api_user.utils_misc import calculate_password_hash


async def db_client() -> AgnosticDatabase:
    """Call this from within your event loop to get beanie setup."""
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    # Note: if ".shp" does not exist, it will be created
    await init_beanie(database=client.shp, document_models=[User, ExperimentDB])
    return client.shp


@asynccontextmanager
async def db_context(app: FastAPI):
    """Initialize application services."""
    app.db = await db_client()
    print("DB-Startup complete")
    yield
    print("DB-Shutdown complete")


async def db_insert_test():
    await db_client()

    # add temporary super-user -> NOTE: NOT SECURE
    admin = User(
        email="alter_Verwalter@admin.org",
        password=calculate_password_hash("""So-@khY"pdM_P/GK--='G?3Bsqg;WC,QuSQH=DCKL4"""),
        role="admin",
        disabled=False,
        email_confirmed_at=local_now(),
        group_confirmed_at=local_now(),
    )
    await User.insert_one(admin)


# TODO: dump to file, restore from it - can beanie or motor do it?
