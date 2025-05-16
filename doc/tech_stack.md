## Cornerstones

### Data-Containers

[Pydantic](https://github.com/pydantic/pydantic)

- data validation for python dataclasses, its fast, elegantly designed and comes with batteries included
- already trusted base for [shepherd-datalib](https://github.com/orgua/shepherd-datalib)

### WebFrontend

[FastUI](https://github.com/pydantic/FastUI)

- restful web-framework based on pydantic2 & fastapi
- still alpha, but usable, rapid updates
- plan B: tbd

[Streamlit](https://streamlit.io)
- stable and lots to offer, but maybe limited for more
- and there is a freemium service

### WebApi

[FastApi](https://fastapi.tiangolo.com/)
- high performance web framework for APIs based on pydantic
- offers features like OAuth, SSL-Encryption (by uvicorn), user-sessions
- **choice for now**

[Flask](https://flask.palletsprojects.com/en/3.0.x/)
- low level but stable framework

### Database

[Beanie](https://github.com/roman-right/beanie)
- async & pydantic-based ODM or MongoDB
- stable, but also actively developed
- **choice for now**

[SQLModel](https://github.com/tiangolo/sqlmodel)
- async & pydantic-based ODM for SQLAlchemy
- still alpha, very slow in development
- has trouble with complex pydantic-models

[ORMDantic](https://github.com/yezz123/ormdantic)
- async & pydantic-based ODM for SQLAlchemy
- currently limited to pydantic <v2 -> dealbreaker

### Misc

- Secrets-Management
  - https://pypi.org/project/python-secrets/
- Server-Monitoring, remote alerting
  - sentry-sdk,
