from shepherd_client import AdminClient

client = AdminClient()

restrictions = client.get_restrictions()
print(restrictions)

commands = client.get_commands()
print(commands)
