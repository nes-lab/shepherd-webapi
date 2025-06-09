"""With saved credentials the login/authentication is simplified."""

# start example
from shepherd_client import Client

client = Client()
print(client.get_user_info())
# end example
