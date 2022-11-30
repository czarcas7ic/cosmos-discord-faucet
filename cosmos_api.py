import configparser
import json
import logging
import sys
import time

from tabulate import tabulate
from cosmospy import privkey_to_address, seed_to_privkey
from mospy import Account, Transaction
from mospy.clients import HTTPClient
c = configparser.ConfigParser()
c.read("config.ini", encoding='utf-8')

# Load data from config
VERBOSE_MODE          = str(c["DEFAULT"]["verbose"])
DECIMAL               = float(c["CHAIN"]["decimal"])
REST_PROVIDER         = str(c["REST"]["provider"])
MAIN_DENOM            = str(c["CHAIN"]["denomination"])
RPC_PROVIDER          = str(c["RPC"]["provider"])
CHAIN_ID              = str(c["CHAIN"]["id"])
BECH32_HRP            = str(c["CHAIN"]["BECH32_HRP"])
GAS_PRICE             = int(c["TX"]["gas_price"])
GAS_LIMIT             = int(c["TX"]["gas_limit"])
FAUCET_PRIVKEY        = str(c["FAUCET"]["private_key"])
FAUCET_SEED           = str(c["FAUCET"]["seed"])
if FAUCET_PRIVKEY == "":
    FAUCET_PRIVKEY = str(seed_to_privkey(FAUCET_SEED).hex())

FAUCET_ADDRESS    = str(c["FAUCET"]["faucet_address"])
EXPLORER_URL      = str(c["OPTIONAL"]["explorer_url"])

faucet_account = Account(
    seed_phrase=FAUCET_SEED,
    hrp="lava@",
    eth=False,
)

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)


def coins_dict_to_string(coins: dict, table_fmt_: str = "") -> str:
    headers = ["Token", "Amount (ulava)", "amount / decimal"]
    hm = []
    """
    :param table_fmt_: grid | pipe | html
    :param coins: {'clink': '100000000000000000000', 'chot': '100000000000000000000'}
    :return: str
    """
    for i in range(len(coins)):
        hm.append([list(coins.keys())[i], list(coins.values())[i], int(int(list(coins.values())[i]) / DECIMAL)])
    d = tabulate(hm, tablefmt=table_fmt_, headers=headers)
    return d


async def async_request(session, url, data: str = ""):
    headers = {"Content-Type": "application/json"}
    try:
        if data == "":
            async with session.get(url=url, headers=headers) as resp:
                data = await resp.text()
        else:
            async with session.post(url=url, data=data, headers=headers) as resp:
                data = await resp.text()

        if type(data) is None or "error" in data:
            return await resp.text()
        else:
            return await resp.json()

    except Exception as err:
        return f'error: in async_request()\n{url} {err}'


async def get_addr_balance(session, addr: str, denom: str = MAIN_DENOM):
    d = ""
    coins = {}
    try:
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/bank/v1beta1/balances/{addr}/by_denom?denom={denom}')
        if "balance" in str(d):
            return d["balance"]["amount"]
        else:
            return 0
    except Exception as addr_balancer_err:
        logger.error("not able to query balance", d, addr_balancer_err)


async def get_addr_all_balance(session, addr: str):
    d = ""
    coins = {}
    try:
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/bank/v1beta1/balances/{addr}')
        if "balances" in str(d):
            for i in d["balances"]:
                coins[i["denom"]] = i["amount"]
            return coins
        else:
            return 0
    except Exception as addr_balancer_err:
        if VERBOSE_MODE == "yes":
            logger.error(addr_balancer_err)
        return 0


async def get_address_info(session, addr: str):
    try:
        """:returns sequence: int, account_number: int, coins: dict"""
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/auth/v1beta1/accounts/{addr}')
        acc_num = int(d['account']['account_number'])
        try:
            seq = int(d['account']['sequence']) or 0

        except:
            seq = 0
        logger.info(f"faucet address {addr} is on sequence {seq}")
        return seq, acc_num

    except Exception as address_info_err:
        if VERBOSE_MODE == "yes":
            logger.error(address_info_err)
        return 0, 0


async def get_node_status(session):
    url = f'{RPC_PROVIDER}/status'
    return await async_request(session, url=url)


async def get_transaction_info(session, trans_id_hex: str):
    time.sleep(6)
    url = f'{REST_PROVIDER}/cosmos/tx/v1beta1/txs/{trans_id_hex}'
    resp = await async_request(session, url=url)
    return resp


async def send_tx(session, recipient: str, amount: int) -> str:
    url_ = f'{REST_PROVIDER}/cosmos/tx/v1beta1/txs'
    try:
        faucet_account.next_sequence, faucet_account.account_number = await get_address_info(session, FAUCET_ADDRESS)

        tx = Transaction(
            account=faucet_account,
            gas=GAS_LIMIT,
            memo="The first faucet tx!",
            chain_id=CHAIN_ID,
        )

        tx.set_fee(
            denom="ulava",
            amount=GAS_PRICE
        )

        tx.add_msg(
            tx_type="transfer",
            sender=faucet_account,
            receipient=recipient,
            amount=amount,
            denom=MAIN_DENOM,
        )

        client = HTTPClient(api=REST_PROVIDER)

        tx_response = client.broadcast_transaction(transaction=tx)
        return tx_response

    except Exception as reqErrs:
        if VERBOSE_MODE == "yes":
            logger.error(f'error in send_txs() {REST_PROVIDER}: {reqErrs}')
        return f"error: {reqErrs}"


async def gen_transaction(recipient_: str, sequence: int, denom: list, account_num: int, amount_: list,
                          gas: int = GAS_LIMIT, memo: str = "", chain_id_: str = CHAIN_ID,
                          fee: int = GAS_PRICE, priv_key: str = FAUCET_PRIVKEY):

    tx = Transaction(
        privkey=bytes.fromhex(priv_key),
        account_num=account_num,
        sequence=sequence,
        fee_denom=MAIN_DENOM,
        fee=fee,
        gas=gas,
        memo=memo,
        chain_id=chain_id_,
        hrp=BECH32_HRP,
        sync_mode="sync"
    )
    if type(denom) is list:
        for i, den in enumerate(denom):
            tx.add_transfer(recipient=recipient_, amount=amount_[i], denom=den)

    else:
        tx.add_transfer(recipient=recipient_, amount=amount_[0], denom=denom[0])
    return tx


def gen_keypair():
    """:returns address: str, private_key: str, seed: str"""
    new_wallet = generate_wallet(hrp=BECH32_HRP)
    return new_wallet["address"], new_wallet["private_key"].hex(), new_wallet["seed"]
