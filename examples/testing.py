from pathlib import Path

print((Path(__file__).parent / "db.sqlite3").as_posix())
