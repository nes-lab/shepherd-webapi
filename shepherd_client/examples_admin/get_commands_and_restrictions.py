from shepherd_client import AdminClient

client = AdminClient()

restrictions = client.get_restrictions()
print(restrictions)

commands = client.get_commands()
print(commands)

if False:
    client.send_command("stop-scheduler")
    client.send_command("restart")

if False:
    restrictions = [
        "Breaking changes! Update client to version >= 2026.2.2",
    ]
    client.set_restrictions(restrictions)
