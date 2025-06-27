from shepherd_client import AdminClient

client = AdminClient()

client.change_account_state("mail@fail.com", enabled=False)
