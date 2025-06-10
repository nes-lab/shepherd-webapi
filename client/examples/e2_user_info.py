"""Minimal Example for querying user info.

With saved credentials the login/authentication is simplified to a one-liner.

User-info informs you about:

- custom quota (can be modified by an admin)
- current quota boundaries
- remaining free storage on the server
- role and other account data
"""

# start example
from shepherd_client import Client

client = Client()

for key, value in client.get_user_info().items():
    print(f"{key}:\t{value}")
# end example
