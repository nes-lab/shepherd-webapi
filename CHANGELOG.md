# History of Changes

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
