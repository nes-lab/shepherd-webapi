## Layout of Config

### Option 1

<name>:
    type: <type>
    parameters:
        <param1>: <value1>

- clean and easy when there is no encapsulation

### Option 2

<name>-<type>:
    <param1>: <value1>

- flatter for encapsulated content - but harder to implement

#### Option 3

<type>:
    <param1>: <value1>

- flatter, but only viable when there is just one of each


TODO:

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
