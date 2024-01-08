from asyncio import run as aiorun
from pathlib import Path

from ormdantic import Ormdantic

connection = "sqlite+aiosqlite:///" + (Path(__file__).parent / "db.sqlite3").as_posix()
print(connection)
db = Ormdantic(connection)
aiorun(db.init())

print(db._crud_generators.keys())
