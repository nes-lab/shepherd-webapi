# Schepherd-Client

[![PyPIVersion](https://img.shields.io/pypi/v/shepherd_client.svg)](https://pypi.org/project/shepherd_client)
[![PyVers](https://img.shields.io/pypi/pyversions/shepherd_client.svg)](https://pypi.python.org/pypi/shepherd-client)
[![QA-Tests](https://github.com/nes-lab/shepherd-webapi/actions/workflows/quality_assurance.yaml/badge.svg)](https://github.com/nes-lab/shepherd-webapi/actions/workflows/quality_assurance.yaml)

**Shepherd Nova Testbed**: https://testbed.nes-lab.org/

**Testbed-WebAPI**: <https://shepherd.cfaed.tu-dresden.de:8000>

**Source Code**: <https://github.com/nes-lab/shepherd-webapi>

**Main Project**: <https://github.com/nes-lab/shepherd>

---

The Testbed-Client links the user to the testbed.
It's written in Python and uses http-requests to communicate with the web-API.
As the source is open, you can modify and extend it as you like.
You could also write your own tools based on these few hundred lines of code.

## Features

- register & delete an account
- query user information
- create, schedule, query state of experiments
- download results

In the near future, the functionality will be extended to:

- list content like available energy environments, firmwares, virtual power sources (currently hardcoded in shepherd-core)
- query the testbed data-model (currently hardcoded in shepherd-core)
- query state of the observers (last seen alive)
- query statistics on the scheduler-queue
- CLI

## Getting started

### Install

You can install the client by using the package-manager of your choice. In the following example we show pip and uv:

```Shell
pip3 install shepherd-client -U
# or modern uv with automatic virtual environment
uv pip install shepherd-client -U
```

Newest features can be obtained by directly installing from GitHub:

```shell
uv pip install git+https://github.com/nes-lab/shepherd-webapi.git@main
```

### Usage

The current interface is introduced in 5 short examples in the example-directory.
