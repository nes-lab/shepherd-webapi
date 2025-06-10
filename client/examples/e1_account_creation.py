"""Minimal example for creating an account.

If you are interested in trying out the testbed, please contact us via mail: <testbed@nes-lab.org>.
We will provide you a registration-token in time.
This token is bound to the e-mail address and allows creating an account.

You have the option to save your credentials in your XDG-config-directory
(i.e. $HOME/.config/shepherd).
That way you can safely host your future scripts in public repositories.
For registering an account you can fill out & run the following snippet once.

A few notes to explain the behavior:

- registration is possible as soon as you receive the token via mail
- passwords need to be between 10 and 64 characters (all printable ASCII are allowed)
- if you omit the password, the client will create a custom one for you
- it is possible to trigger a forgot-password-routine (you can also back up the config-file)
- choosing `save_credentials` will overwrite the local config (or create a new one)

Once saved, you can omit the credentials, as shown in the next examples.
"""

# start example
from shepherd_client import Client

client = Client("my@mail.com", password="1234", save_credentials=True)
client.register_user(token="XYZ")
# end example
