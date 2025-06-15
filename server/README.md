# Shepherd-Server

## Install Tools

Installation uses uv to install program for everyone.

```Shell
# install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# make herd and server usable as CLI-tool
uv tool install shepherd-herd
uv tool install git+https://github.com/nes-lab/shepherd-webapi.git@main#subdirectory=server
# OR - source newest commits from git
uv tool install git+https://github.com/nes-lab/shepherd@main#subdirectory=software/shepherd-herd
uv tool install --with git+https://github.com/nes-lab/shepherd@dev#subdirectory=software/shepherd-herd git+https://github.com/nes-lab/shepherd-webapi.git@main#subdirectory=server --force
```

Create an admin account with:

```Shell
shepherd-server create-admin mail@dail.de password
```

## Prepare Config

There is more than one way to alter the server configuration.
Currently, the services expect variables set in `/home/service/.env`.
Additionally, the `herd.yaml` can be put in `/etc/shepherd/`.
Same for the SSL-key & -certificates.

## Prepare folders

Add network-storage and make sure the server can access the data.
The following command adds read and write to all files and subdirectories in `/var/shepherd`:

```Shell
 sudo chmod a+rw -R /var/shepherd
```

## Install MongoDB

The [official setup-guide](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/) was used without complications.
To test for success a simple cmd is enough:

```Shell
sudo systemctl status mongod
```

## Install Services

Services are currently hard-linked to the above tooling in the account `service`.

```Shell
sudo cp /opt/shepherd_webservice/playground/prototype_fastapi/shepherd-api.service /etc/systemd/system/
sudo systemctl start shepherd-api
sudo systemctl enable shepherd-api

sudo cp /opt/shepherd_webservice/playground/prototype_fastapi/shepherd-redirect.service /etc/systemd/system/
sudo systemctl start shepherd-redirect
sudo systemctl enable shepherd-redirect

sudo cp /opt/shepherd_webservice/playground/prototype_fastapi/shepherd-scheduler.service /etc/systemd/system/
sudo systemctl start shepherd-scheduler
sudo systemctl enable shepherd-scheduler

# check with
sudo systemctl status shepherd-api
sudo systemctl status shepherd-redirect
sudo systemctl status shepherd-scheduler
sudo journalctl -n 20 -u shepherd-* --follow
```
