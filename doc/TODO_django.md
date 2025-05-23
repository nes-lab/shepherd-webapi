# Django TODO

Kept in here for the time being - because 2nd half has thoughts about datastructures.

## Short-term

large parts are related to django (but not all)

django-questions
- can we delete empty files like admin.py?
- form to documentation, how?

Later:
- analyzers for codequality, coverage, maintainability

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
  - **https://django-allauth.readthedocs.io/en/latest/installation.html**
  - https://python-social-auth.readthedocs.io/en/latest/backends/github.html
  - Services: github, bitbucket, gitlab, stackoverflow
- Rest-Framework
  - https://www.django-rest-framework.org/

- YAML as POST-source
  - https://jpadilla.github.io/django-rest-framework-yaml/
- Form, automatic layouts
  - crispy: https://pypi.org/project/django-crispy-forms/
    - https://django-crispy-forms.readthedocs.io/en/latest/
- try poetry instead of pipenv and other setup-tools?
  - https://python-poetry.org/docs/basic-usage/
- use forge instead of django? more constrained fork
  - https://github.com/forgepackages/forge


- models of data-structures
  - django-internal -> should be independent of django, but I see no alternative atm
  - validation (cross-field): https://github.com/shezadkhan137/required
  - transformation: https://convtools.readthedocs.io/en/latest/index.html#ref-index-intro
  - pydantic-models: https://pydantic-docs.helpmanual.io/usage/exporting_models/
  - djantic: https://jordaneremieff.github.io/djantic/
  - idea: django-model -> djantic -> pydantic -> dict -> yaml
- view Data (list or individual elements)
  - https://pypi.org/project/django-static-models/
  -

Alternative Bases:
- Panel, www.awesome-panel.org
  - Streamz, https://streamz.readthedocs.io
  - Param, https://param.holoviz.org/
    - Param for django https://pypi.org/project/django-param/
  - Pydantic, https://pydantic-docs.helpmanual.io/
-


## Data-Structures

- **bold** ones are mandatory
- allow down- and upload for admin
  - testbed setup
- experiments should document itself (reread directory for )
- TODO:
  - which nodes
  - firmware

### Form-Design in Django

General Form-Design:
- proper Elements
  - CharField instead of textField (better documentation, smaller field?)
  - SlugField to force only letters, numbers, underscores, hyphens
  -
- documentation and common options
  - verbose_name
  - help_text
  - blank -> allow empty
  - null -> allow nonexistence
  - unique -> content can only be used once
  - primary_key
  - editable
- extra doc -> use docstring, reference other models with :model:'testbed.Target' for example

### User

- **name**
- **email**
- **pw**
- Groups / Team

internal:
- oauth2-data
- ID
- storage_cap (all data)
- storage_current
- duration_cap (last 7 days?)
- duration_current

### Groups / Team

- **name**
- description
- locked - only members can add new users

internal:
- ID

### Experiment

On Creation:
- **name**
- description
- custom
- **schedule**
- group
- state: prototype, scheduled, in progress, postprocessing, finished (downloadable)
  - https://django-model-utils.readthedocs.io/en/latest/fields.html#statusfield
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
  - https://django-model-utils.readthedocs.io/en/latest/models.html#timeframedmodel + manager

internal:
- setup-duration (something like 120s + 10% of duration if power-)
- finish-duration
- experiment-ID

### Target-Setup (elements of experiment)

- **Observer-IDs**
- Target-IDs
- vSource
  - config-classes (hopefully derivable from core-lib)
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
- result-stat: char-count, transmissions / CR-count
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
