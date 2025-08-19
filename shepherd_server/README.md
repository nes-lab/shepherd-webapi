# Shepherd-Server

The WebAPI-Server links the user to the testbed.
It's written in Python and uses FastAPI to expose an interface to the internet.
You can write your own tools or just use the testbed-client integrated in the [core-lib](https://pypi.org/project/shepherd_core).

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

## Backup & Restore State of DB

Install MongoDB database tools on the server running the database via <https://www.mongodb.com/docs/database-tools/installation/>

Backup and restore with:

```Shell
mongodump --out=~/mongo-backup/
mongorestore ~/mongo-backup/
```

or to get YAML-files (not working ATM)

```
shepherd_server backup dir_path
shepherd_server init dir_path
```

## Full Setup-Guide

### Prepare Server

- DNS approved for the server: <https://shepherd.cfaed.tu-dresden.de>
- Port 8000 accepted for firewall passing
- ~~SSL-Certificate per LetsEncrypt -> alternative is <www.sectigo.com>~~

[API-Website](http://127.0.0.1:8000/)
[ReDoc](http://127.0.0.1:8000/doc)
[OpenApiDoc](http://127.0.0.1:8000/doc0)

### Install Tools

Installation uses uv to install program for everyone.

```Shell
# install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# make herd and server usable as CLI-tool
uv tool install git+https://github.com/nes-lab/shepherd-webapi.git@main#subdirectory=shepherd_server
uv tool install shepherd-herd
# OR - source newest commits from git
uv tool install git+https://github.com/nes-lab/shepherd@main#subdirectory=software/shepherd-herd
```

Create an admin account with:

```Shell
shepherd-server create-admin mail@dail.de password
```

### SSL-Certificates

Certbot can be used to generate and renew certificates for https.
Certs are free of charge and valid for 90 days (as of 2025).
Install on server via:

```Shell
sudo apt install certbot
# for running services you can enter
sudo certbot certonly --webroot
```

The feedback will be:

```
Please enter the domain name(s) you would like on your certificate (comma and/or
space separated) (Enter 'c' to cancel): shepherd.cfaed.tu-dresden.de
Requesting a certificate for shepherd.cfaed.tu-dresden.de

Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/shepherd.cfaed.tu-dresden.de/fullchain.pem
Key is saved at:         /etc/letsencrypt/live/shepherd.cfaed.tu-dresden.de/privkey.pem
This certificate expires on 2025-10-07.
These files will be updated when the certificate renews.
Certbot has set up a scheduled task to automatically renew this certificate in the background.
```

Certbot will automatically renew certificates from now on.
The config for the webservices can point directly to these files.

Further reading:
- https://eff-certbot.readthedocs.io/en/stable/using.html#id8
- https://certbot.eff.org/faq/

### Prepare Config

There is more than one way to alter the server configuration.
Currently, the services expect variables set in `/home/service/.env`.
Additionally, the `herd.yaml` can be put in `/etc/shepherd/`.
Same for the SSL-key & -certificates.

Config `.env`, by either bringing in a backup or starting fresh

- email-server needs credentials
- backup: repopulate database by using ´shepherd_server init file´
- fresh start: generate [fresh salt](https://github.com/nes-lab/shepherd-webapi/blob/main/shepherd_server/scripts/salt_generator.py) and initialize database with `shepherd_server init`

```ini
# Secrets
SECRET_KEY="abc"
AUTH_SALT='cde'

# Https
SSL_KEYFILE="/etc/letsencrypt/live/shepherd.cfaed.tu-dresden.de/privkey.pem"
SSL_CERTFILE="/etc/letsencrypt/live/shepherd.cfaed.tu-dresden.de/fullchain.pem"

# FastMail
MAIL_ENABLED=true
MAIL_USERNAME="testbed@test.bed"
MAIL_PASSWORD="pass-the-word"
```

### Prepare folders

Add network-storage and make sure the server can access the data.
The following command adds read and write to all files and subdirectories in `/var/shepherd`:

```Shell
 sudo chmod a+rw -R /var/shepherd
```

### Install & test Dependencies

- set up a local [MongoDB](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/) instance
- shepherd-herd should have access to all observers
- extra filesystem should be mounted symmetrically (same path on server & observers)

The [official setup-guide](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/) was used without complications.
To test for success a simple cmd is enough:

```Shell
sudo systemctl status mongod
```

### Install Services

Services are currently hard-linked to the above tooling in the account `service`.

```Shell
sudo cp /opt/shepherd_webservice/shepherd_server/shepherd-api.service /etc/systemd/system/
sudo systemctl start shepherd-api
sudo systemctl enable shepherd-api

sudo cp /opt/shepherd_webservice/shepherd_server/shepherd-redirect.service /etc/systemd/system/
sudo systemctl start shepherd-redirect
sudo systemctl enable shepherd-redirect

sudo cp /opt/shepherd_webservice/shepherd_server/shepherd-scheduler.service /etc/systemd/system/
sudo systemctl start shepherd-scheduler
sudo systemctl enable shepherd-scheduler

# check with
sudo systemctl status shepherd-api
sudo systemctl status shepherd-redirect
sudo systemctl status shepherd-scheduler
sudo journalctl -n 20 -u shepherd-* --follow --all
```
