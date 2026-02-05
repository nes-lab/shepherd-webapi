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
        "BatteryModel is not integrated yet, so an older core-lib is needed (2025.8.1)",
    ]
    client.set_restrictions(restrictions)
