# History of Changes

## v2026.02.2

- switch to newest core-lib -> **breaking changes**!
- users can now use the new battery-model for the virtual source
- users can now use the new energyEnvironment-model

## v2026.02.1

### API

- scheduling an experiment is now only possible if paths are contained within a restricted set
- improvements for mails
- add endpoints in `/testbed` for hardware:
  - `/testbed/observer`,
  - `/testbed/cape`,
  - `/testbed/target`,
- add endpoints in `/content` for EEnvs, VSrc, VHrv
  - `/content/EnergyEnvironment`,
  - `/content/VirtualHarvesterConfig`,
  - `/content/VirtualSourceConfig`,
  - these endpoints are currently driven by the fixtures from core-lib
- add `experiments/id/statistics`-endpoint to get metadata useful for statistics
  - this currently contains ID, state, execution-time, duration, size, owner
- fix build-script

### Client

- fix output of .list_experiments() to only output lists of IDs
- admins are now able to read IDs and basic stats of all experiments (runtime, state, start-time, user)

### General

- improve documentation
- packages now support py314
- update deprecated metadata in pyproject.toml
- workflows use py314 as default
- workflows use uv fully
- add section in server-readme to fix permissions for reading systemd-journal
- switch from pre-commit to prek
- move version-handling completely to pyproject.toml

## v2025.10.1

- upgrade server to py313 (automatic DL via uv)
- rename package-directories to `shepherd_client` & `shepherd_server`
- pin shepherd-core version
- extend services to autostart / depend on mongo-DB
- handle deprecation-warnings of sub-packages
- fix bug not enabling verbose mode on CLI
- update tooling

## v2025.08.2

- migrate server to beanie v2

## v2025.08.1

- add admin-client, that can
  - approve accounts
  - enable / disable accounts
  - extend quota
  - get / set restrictions
  - get / send commands (mostly for observers)
- scheduler
  - optimize delays of scheduler (from > 5min per experiment, to < 3 min)
  - add reboot of observers when an experiment fails (~ 10 min delay, admin is notified)
  - refactor code after kinks of ssh, observers & file-server were figured out
  - use 1 static herd (avoids fabric bugs)
  - herd only uses requested observers (that are also online)
  - improve status mails
  - disable tqdm progress bar for herd and sheep to get cleaner logs
  - get specific logs of scheduler and observers by querying journalctl with `--since`
- server
  - allow deactivating accounts
  - add admin functionality
  - database models are validated before being saved (avoids broken DB)
  - add async-wrapper for blocking functions that removes lots of boilerplate code
- python - replace pipenv & setuptools by uv

## v2025.06.4

- client
  - add support for changed root-router
  - add support for commands
  - rename _user()-functions to _account()
- server
  - extend status information on root-router
  - improve handling of observer states and outputs
  - improve result-mail (with granular reasoning)
  - improve scheduler (much more robust, less wasting time by polling)
  - add queue-log-handler for less blocking logging
  - add routes for restrictions
  - elevated users can execute commands (restart, resync, ...)
- python - allow to install packets with .[all]

## v2025.06.3

- client - add experiment config to downloaded files
- server
  - fix missing SSL CA
  - improve scheduler (synced start, more robust, more meta information)
  - improve result-mail (add error-log of faulty nodes, add list of missing nodes, number and size of result-files)
  - make saving database-entries safer with .save_changes()

## v2025.06.2

- client - now warns if scheduler is not running or API is inaccessible
- server
  - root URL has status-info about the testbed (scheduler, observers, ...)
  - send emails when xp are done (if activated in config) or scheduler has no more tasks from you
  - send emails to admin and user if experiment failed (with error-log)
  - improve scheduler - handle edge-cases and collect files afterward
  - deleting an experiment now also deletes the directories (and by-products)
  - put server-tasks into systemd-services that run with local account

## v2025.06.1

- added client that allows
  - creating / registering account and also deleting it
  - create & schedule experiments
  - get information about experiments and user-data
  - download & delete experiments
- server
  - has now more secure way of account creation (users get approved for registration)
  - can prune data (unused accounts, old experiments)
  - allow bootstrapping database by creating an admin via CLI
  - passwords are now limited to printable ASCII with 10 - 64 chars
  - fix scheduler
  - list-experiments now only returns UUIDs and their state
  - the experiment-config is updated with the exact starting-time after scheduler finishes

## v2025.05.1

- first working prototype
