# Shepherd-WebAPI

[![PyPIVersion](https://img.shields.io/pypi/v/shepherd_client.svg)](https://pypi.org/project/shepherd_client)
[![QA-Tests](https://github.com/nes-lab/shepherd-webapi/actions/workflows/quality_assurance.yaml/badge.svg)](https://github.com/nes-lab/shepherd-webapi/actions/workflows/quality_assurance.yaml)

**Testbed-WebAPI**: <https://shepherd.cfaed.tu-dresden.de:8000>

**Main Documentation**: <https://nes-lab.github.io/shepherd>

**Source Code**: <https://github.com/nes-lab/shepherd-webapi>

**Main Project**: <https://github.com/nes-lab/shepherd>

---

This repo contains:

- `shepherd-client`-sources in `/client`
- `shepherd-server`-sources in `/server`

## Development & Release

The project contains a config for dev-environment in the root `pyproject.toml`.
It can be activated via `uv`:

```Shell
uv venv
uv pip install .
```

### Testbench & Static Analysis

**Warning**: ☠☠☠ Don't run unittests (`pytest`) on a production system as it will delete the database! ☠☠☠

```Shell
pre-commit run -a

pytest
# or
pytest --stepwise
```

### Code Coverage

```shell
coverage run -m pytest

coverage html
# or simpler
coverage report
```

## Release-Procedure

- increase version number by executing ``bump2version`` (see cmds below)
- update changelog in ``CHANGELOG.md``
- run unittests locally
  - additionally every push gets automatically tested by GitHub workflows
- install and run ``pre-commit`` for QA-Checks, see steps above
- move code from dev-branch to main by PR
- add tag to commit - reflecting current version number - i.e. ``v25.5.1``
  - GitHub automatically creates a release
- update release-text with latest Changelog (from `CHANGELOG.md`)
- rebase dev-branch

```Shell
bump2version --allow-dirty --new-version 2025.08.1 patch
# ⤷ format: year.month.patch_release
```
