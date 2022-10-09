import httpx # optional
from mospy import Account, Transaction
from mospy.clients import HTTPClient

account = Account(
    seed_phrase="enlist jar utility clog satoshi advance worth hundred style lemon know faith quick wedding decline vital broom approve patrol history dinosaur area kangaroo cereal",
    hrp="evmos",
    slip44=60,
    eth=True,
    next_sequence=2,
    account_number=2156925,
)

tx = Transaction(
    account=account,
    gas=2000000,
    memo="The first mospy evmos transaction!",
    chain_id="evmos_9001-2",
)

tx.set_fee(
    denom="aevmos",
    amount=100000000000000000
)
tx.add_msg(
    tx_type="transfer",
    sender=account,
    receipient="evmos1q2r0ljt3zd59fnxvk6amfdddqg7y806ghhxkct",
    amount=100000000000000000,
    denom="aevmos",
)

client = HTTPClient(api="https://api.evmos.interbloc.org")
tx_response = client.broadcast_transaction(transaction=tx)

print(tx_response)