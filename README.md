# Shepherd-WebAPI

[![QA-Tests](https://github.com/nes-lab/shepherd-webapi/actions/workflows/quality_assurance.yaml/badge.svg)](https://github.com/nes-lab/shepherd-webapi/actions/workflows/quality_assurance.yaml)

**Testbed-WebAPI**: <https://shepherd.cfaed.tu-dresden.de:8000>

**Main Documentation**: <https://orgua.github.io/shepherd>

**Source Code**: <https://github.com/nes-lab/shepherd-webapi>

**Main Project**: <https://github.com/orgua/shepherd>

---

The WebAPI links the user to the testbed.
It's written in Python and uses FastAPI to expose an interface to the internet.
You can write your own tools or just use the testbed-client integrated in the [Core-Datalib](https://pypi.org/project/shepherd_core).

Internally the scheduler behind the API utilizes the [herd-lib](https://pypi.org/project/shepherd_herd) to access the shepherd observers.
Handling of data is done with Pydantic-Models that store the actual data in a database.

## Features

- user-management with regular users and elevated admins
- users can store, schedule, query state of experiments
- users can download results
- users have default quotas and may receive custom quotas with expiry date
- system emails state-changes
- scheduler, as interface to the testbed
- redirect http / https to current landing-page
- SSL is automatically enabled if certs are found

## Getting Started

### Prepare Server

- DNS approved for the server: <https://shepherd.cfaed.tu-dresden.de>
- Port 8000 accepted for firewall passing
- SSL-Certificate per LetsEncrypt -> alternative is <www.sectigo.com>
- added [https to FastAPI](https://fastapi.tiangolo.com/deployment/https/)
- TODO: allow service to start with reduced rights -> get nfs in order (access needs elevation)

[API-Website](http://127.0.0.1:8000/)
[ReDoc](http://127.0.0.1:8000/doc)
[OpenApiDoc](http://127.0.0.1:8000/doc0)

### Install Dependencies

- set up a local [MongoDB](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/) instance
- shepherd-herd should have access to all observers
- extra filesystem should be mounted symmetrically (same path on server & observers)
- install the package in this repo, see code below

**NOTE:** the current version needs a special version of shepherd-core, with deep validation disabled.

```Shell
pip install git+https://github.com/nes-lab/shepherd-webapi.git@main

# or modern venv
uv pip install git+https://github.com/nes-lab/shepherd-webapi.git@main

# or old pipenv
git clone https://github.com/nes-lab/shepherd-webapi.git
cd shepherd-webapi
pipenv install
pipenv shell
```

### Update Config

Config `.env`, by either bringing in a backup or starting fresh

- email-server needs credentials
- backup: repopulate database by using ´shepherd_server init file´
- fresh start: generate [fresh salt](https://github.com/nes-lab/shepherd-webapi/blob/main/scripts/salt_generator.py) and initialize database with `shepherd_server init`

```ini
# Secrets
SECRET_KEY="abc"
SALT='cde'

# FastMail
MAIL_CONSOLE=true
MAIL_USERNAME="testbed@test.bed"
MAIL_PASSWORD="pass-the-word"
```

## Command-Line-Interface

```Shell
shepherd-server --verbose run
# or individually (without verbosity)
shepherd-server run-api
shepherd-server run-scheduler
shepherd-server run-redirect
```

Note: the scheduler can

- run in dry-mode (`--dry-run`) that mocks result-data
- receive a custom herd-inventory (`--inventory=path-to-yaml`)

### Backup & Restore State of DB

```Shell
shepherd_server backup file_name
shepherd_server init file_name
```

## Development & Release

### Testbench

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
- run unittests
  - additionally every push gets automatically tested by GitHub workflows
- install and run ``pre-commit`` for QA-Checks, see steps above
- move code from dev-branch to main by PR
- add tag to commit - reflecting current version number - i.e. ``v25.5.1``
  - GitHub automatically creates a release
- update release-text with latest Changelog (from `CHANGELOG.md`)
- rebase dev-branch

```Shell
bump2version --allow-dirty --new-version 25.05.1 patch
# ⤷ format: year.month.patch_release
```
