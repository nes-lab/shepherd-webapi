"""Minimal example for creating an account."""

# start example
from shepherd_client import Client

client = Client("my@mail.com", password="1234", save_credentials=True, debug=True)
client.register_user(token="XYZ")
# end example
