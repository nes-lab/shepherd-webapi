## Short-term


- static websites
  - impressum
  - accessability
  - landing-page
- generate webform from class? constraints for var
- interactive graphics with plotly?
- login via oauth
- email-account shepherd-neslab@tu-dresden.de ? neslab-shepherd@tu-dresden.de
- ssl-certificate
- figure out groups
  - 
- load css and others locally
- secure admin-panel with some random (changing) hash-address
- OneToOneField does not appear in form
- even cleaner form from model? `editable` is there
- dark mode toggle?

django-questions
- can we delete empty files like admin.py?
- form to documentation, how?


## Building-Blocks

- Base -> Django (4.1 currently)
- CSS
  - **[Bootstrap 5](https://blog.getbootstrap.com/)**
  - https://github.com/StartBootstrap/startbootstrap-bare
  - tailwind
- Icons
  - https://fontawesome.com/search?s=light
  - https://fontawesome.com/docs/web/use-with/python-django
- Oauth
  - https://djangopackages.org/grids/g/oauth/?python3=1 -> Client
  - **https://python-social-auth.readthedocs.io/en/latest/backends/github.html**
    - https://github.com/python-social-auth/social-app-django
    - github
    - bitbucket
    - gitlab
    - stackoverflow
- Rest-Framework
  - https://www.django-rest-framework.org/
- Secrets-Management
  - https://pypi.org/project/python-secrets/
- YAML as POST-source
  - https://jpadilla.github.io/django-rest-framework-yaml/
- Form, automatic layouts
  - crispy: https://pypi.org/project/django-crispy-forms/
    - https://django-crispy-forms.readthedocs.io/en/latest/ 
- try poetry instead of pipenv and other setup-tools?
  - https://python-poetry.org/docs/basic-usage/
- use forge instead of django? more constrained fork
  - https://github.com/forgepackages/forge

## Data-Structures

- **bold** ones are mandatory
- allow down- and upload for admin
  - testbed setup
- experiments should document itself (reread directory for )
- TODO: 
  - which nodes
  - firmware

### User

- **name**
- **email**
- **pw**
- Groups

internal:
- oauth2-data
- ID
- storage_cap (all data)
- storage_current
- duration_cap (last 7 days?)
- duration_current

### Groups

- **name**
- description
- locked - only members can add new users

internal:
- ID

### Experiment

- **name**
- description
- custom
- **schedule**
- group
- state: prototype, scheduled, in progress, postprocessing, finished (downloadable)
- **target-setup(s)**

finished:
- runtime_final 
- storage_size
- path_data (usr_group_)
- Services
  - uart
  - energy-trace
  - gpio-tracing
  - gpio-actuation

internal:
- ID
- user-id
- age_max
- scheduled for deletion (age, user non existing)

### Schedule (element of experiment, or other way around)

- start
- **duration**

internal:
- setup-duration (something like 120s + 10% of duration if power-)
- finish-duration
- experiment-ID

### Target-Setup (elements of experiment)

- **Observer-IDs**
- Target-IDs
- vSource
  - config-classes (hopefully derivable from datalib)
  - recorded trace (if needed)
- **imageID** ID of previously uploaded image **OR** **embeddedImage**


### Firmware / images (element of target-setup)

- name
- description
- **ImageID** (hash)
- **content / data**
- **platform** (msp430, nRF52, ...)
- owner: user or group (allow both?)

internal:

### Services

UART

- **observerIDs**
- **port** 
- **baudrate**
- result-stat: char-count, transmissions / cr-count
- 

Power-Profiling

- **observerIDs**
- sample-rate (sampling always with 100 kHz, will be downsampled if needed)
- only current (if voltage is constant)
- (power-conversion)
- time_offset (timer after experiment-start)
- duration (max default)
- (fileformat) h5 preferred, csv in edgecases


GPIO-Tracing

- **observerIDs**
- **Pins**
- time_offset (timer after experiment-start)
- duration (max default)

GPIO-Actuation

- **observerIDs**
- pinAction
  - **pin**
  - **level**
  - **time_offset**
  - period
  - count

### Testbed-Setup

GPIOs
- **name**
- description
- comment
- direction
- pru-monitored
- pin_sys

Target (element of observer)
- **name**
- description
- comment
- platform:
- core:
- programmer: 

Observer
- **name**
- **IP**
- MAC
- room
- port
- ID
- comments
- longitude (decimal degrees, 0.1 udeg ~= 11 mm)
  - https://navigator.tu-dresden.de/etplan/bar/02
- latitude
- target [A1, A2, B1, B2]: name



