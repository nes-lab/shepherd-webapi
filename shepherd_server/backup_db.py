import pathlib
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import beanie
import bson
import yaml
from beanie import Document
from shepherd_core import local_now
from shepherd_core.data_models import Wrapper
from yaml import Node
from yaml import SafeDumper

from shepherd_server.instance_db import db_client
from shepherd_server.logger import log


def path2str(
    dumper: SafeDumper, data: pathlib.Path | pathlib.WindowsPath | pathlib.PosixPath
) -> Node:
    """Add a yaml-representation for a specific datatype."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data.as_posix()))


def time2int(dumper: SafeDumper, data: timedelta) -> Node:
    """Add a yaml-representation for a specific datatype."""
    return dumper.represent_scalar("tag:yaml.org,2002:int", str(int(data.total_seconds())))


def generic2str(dumper: SafeDumper, data: Any) -> Node:
    """Add a yaml-representation for a specific datatype."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.add_representer(UUID, generic2str, SafeDumper)
yaml.add_representer(bson.ObjectId, generic2str, SafeDumper)
yaml.add_representer(beanie.Link, generic2str, SafeDumper)
yaml.add_representer(pathlib.PosixPath, path2str, SafeDumper)
yaml.add_representer(pathlib.WindowsPath, path2str, SafeDumper)
yaml.add_representer(pathlib.Path, path2str, SafeDumper)
yaml.add_representer(timedelta, time2int, SafeDumper)


async def backup_db(doc: type(Document), path: Path) -> Path:
    _client = await db_client()
    models = await doc.all().to_list()
    models_wrap = []

    for model in models:
        model_dict = model.model_dump(exclude_unset=True, exclude_defaults=True)
        model_wrap = Wrapper(
            datatype=doc.__name__,
            created=local_now(),
            parameters=model_dict,
        )
        models_wrap.append(model_wrap.model_dump(exclude_unset=True, exclude_defaults=True))

    models_yaml = yaml.safe_dump(
        models_wrap,
        default_flow_style=False,
        sort_keys=False,
    )
    path_file = path / (doc.__name__ + ".yaml")
    log.info("Backup %d %s-Models to: %s", len(models), doc.__name__, path_file.name)
    with path_file.open("w") as f:
        f.write(models_yaml)
    return path_file
