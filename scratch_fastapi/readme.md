## TODO

- proto 2 with the config scheme proposed above
  - automatic switcher for wrapped files or typed inputs- DB-backend
- completion-guide
- fully describe API
  - integrate all needed fields
  - test lists

- create forms from model
-

- tests with
  - from fastapi.testclient import TestClient
  - https://fastapi.tiangolo.com/tutorial/testing/
- use metadata tags to describe the items in redoc (https://fastapi.tiangolo.com/tutorial/metadata/)

- integrate pydantic into django
  - guide: https://testdriven.io/blog/django-and-pydantic/
  - djantic (pydantic-django) https://github.com/jordaneremieff/djantic
    - django models with pydantic functionality
    - TODO: initialize by pydantic model?
  - django-ninja
    - api-documentation from fastapi
    - FAST
    - fastapi style integrated into django

# Install Dummy API

```Shell
sudo pip install fastapi uvicorn shepherd-core python-multipart -U

cd /opt
sudo git clone https://github.com/orgua/shepherd_webservice
sudo cp /opt/shepherd_webservice/scratch_fastapi/shepherd-web.service /etc/systemd/system/
sudo systemctl start shepherd-web
sudo systemctl enable shepherd-web

# check with
sudo systemctl status shepherd-web
sudo journalctl -n 20 -u shepherd-web
```

TODO:

- create minimal user for service
- get nfs-rigts-management straigt
- integrate all that into python-package
