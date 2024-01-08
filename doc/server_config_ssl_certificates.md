# SSL / HTTPs for FastApi / Uvicorn

Fastapi has [documentation about https](https://fastapi.tiangolo.com/deployment/https/)

Domain: <shepherd.cfaed.tu-dresden.de>

Start with [LetsEncrypt](https://letsencrypt.org/getting-started/)

## Certbot

[installation for ubuntu](https://certbot.eff.org/instructions?ws=other&os=ubuntufocal&tab=standard)

**fails**: needs accessible port 80

```Shell
# pre-reqs
sudo apt install snapd
# cleanup
sudo apt remove certbot
# install
sudo snap install --classic certbot
# test
sudo ln -s /snap/bin/certbot /usr/bin/certbot
# spin webserver and get certificate (needs domain-name & email-address)
sudo certbot certonly --standalone
sudo certbot certonly --webroot
```

## Self-signed SSL with mkcert

```Shell
# prereqs
sudo apt install libnss3-tools mkcert

mkcert -install
cd /etc/shepherd/
mkcert shepherd.cfaed.tu-dresden.de localhost 127.0.0.1 ::1
```

profiles (valid 2+ years) now at

```Shell
/etc/shepherd/shepherd.cfaed.tu-dresden.de+3-key.pem
/etc/shepherd/shepherd.cfaed.tu-dresden.de+3.pem
```

## Uvicorn + fastApi

<https://www.uvicorn.org/deployment/#running-with-https>

add arguments

```Shell
--ssl-keyfile=/etc/shepherd/shepherd.cfaed.tu-dresden.de+3-key.pem
--ssl-certfile=/etc/shepherd/shepherd.cfaed.tu-dresden.de+3.pem
```

also add http-redirect, see </scratch_fastapi>

[try in browser](shepherd.cfaed.tu-dresden.de:8000)
