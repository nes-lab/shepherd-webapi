"""Generate a new bcrypt password salt and updates to local .env file."""

from hashlib import sha3_512
from pathlib import Path

from shepherd_core.data_models.base.timezone import local_iso_date

path_project = Path(__file__).parent.parent
path_env = path_project / ".env"
env = path_env.read_text()
target = 'SECRET_KEY="'
start = env.find(target) + len(target)
prefix, postfix = env[:start], env[start:]
end = postfix.find('"')
output = prefix + sha3_512(local_iso_date().encode("UTF-8")).hexdigest()[:64] + postfix[end:]
with path_env.open("w") as out:
    out.write(output)
