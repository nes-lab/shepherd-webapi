# History of Changes

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
