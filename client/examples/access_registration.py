"""Minimal example for creating an account."""

# start example
from shepherd_client import Client

# CLI: shepherd-server create-admin ingmar.splitt@tu-dresden.de 1234567890

with Client()


client = Client("my@mail.com", password="1234", save_credentials=True, debug=True)
client.register_user(token="XYZ")
# end example
