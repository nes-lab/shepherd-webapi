"""Generate a new bcrypt password salt and updates to local .env file."""

from pathlib import Path

import bcrypt

path_project = Path(__file__).parent.parent
path_env = path_project / ".env"
env = path_env.read_text()
target = 'AUTH_SALT="'
start = env.find(target) + len(target)
prefix, postfix = env[:start], env[start:]
end = postfix.find('"')
output = prefix + str(bcrypt.gensalt()) + postfix[end:]
with path_env.open("w") as out:
    out.write(output)
