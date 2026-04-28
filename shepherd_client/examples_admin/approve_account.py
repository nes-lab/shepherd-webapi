from shepherd_client import AdminClient

client = AdminClient()

token = client.approve_account("mail@fail.com")

print(f"Account was approved with token: {token}")
