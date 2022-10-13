import configparser
from tabulate import tabulate
import logging 
import sys
import time
import os

from mospy import Account, Transaction
from mospy.clients import HTTPClient
from mospy.utils import seed_to_private_key
from dotenv import load_dotenv

import aiohttp
import asyncio

from decimal import Decimal

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

c = configparser.ConfigParser()
c.read("config.ini", encoding='utf-8')

load_dotenv()
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
FAUCET_PRIVKEY        = os.getenv("PRIVATE_KEY")
FAUCET_SEED           = os.getenv("FAUCET_SEED")
if FAUCET_PRIVKEY == "":
    FAUCET_PRIVKEY = str(seed_to_private_key(FAUCET_SEED).hex())

FAUCET_ADDRESS    = str(c["FAUCET"]["faucet_address"])
EXPLORER_URL      = str(c["OPTIONAL"]["explorer_url"])

faucet_account = Account(
    seed_phrase=FAUCET_SEED,
    hrp="evmos",
    slip44=60,
    eth=True,
)
print(FAUCET_SEED)
logger.info(f"faucet address {faucet_account.address} initialized")


def coins_dict_to_string(coins: dict, table_fmt_: str = "") -> str:
    headers = ["Token", "Amount"]
    hm = []
    """
    :param table_fmt_: grid | pipe | html
    :param coins: {'clink': '100000000000000000000', 'chot': '100000000000000000000'}
    :return: str
    """
    for i in coins:
        hm.append([i, coins[i]])
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


async def get_addr_evmos_balance(session, addr: str, denom: str):
    d = ""
    coins = {}
    try:
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/bank/v1beta1/balances/{addr}/by_denom?denom={denom}')
        if "balance" in str(d):
            return await aevmos_to_evmos(d["balance"]["amount"])
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
                
                if i["denom"] == "aevmos":
                    coins["evmos"] = coins.pop(i["denom"])
                    coins["evmos"] = await aevmos_to_evmos(i["amount"])

            return coins
        else:
            return 0
    except Exception as addr_balancer_err:
        print("get_addr_balance", d, addr_balancer_err)

async def get_address_info(session, addr: str):
    try:
        """:returns sequence: int, account_number: int, coins: dict"""
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/auth/v1beta1/accounts/{addr}')

        acc_num = int(d['account']['base_account']['account_number'])
        try:
            seq = int(d['account']['base_account']['sequence']) or 0
            
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
    url = f'{REST_PROVIDER}/cosmos/tx/v1beta1/txs/{trans_id_hex}'
    time.sleep(6)
    resp = await async_request(session, url=url)
    if 'height' in str(resp):
        return resp
    else:
        return f"error: {trans_id_hex} not found"


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
        denom="aevmos",
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
        tx_response =  client.broadcast_transaction(transaction=tx)
        logger.info(tx_response)
        return tx_response

    except Exception as reqErrs:
        if VERBOSE_MODE == "yes":
            print(f'error in send_txs() {REST_PROVIDER}: {reqErrs}')
        return f"error: {reqErrs}"

async def aevmos_to_evmos(aevmos):
    aevmos_ = float(aevmos)
    amount_evmos = aevmos_/DECIMAL
    logger.info(f"Converted {aevmos_} aEvmos to Evmos {amount_evmos}")
    return f'{amount_evmos}'

# async def test():
#     session = aiohttp.ClientSession()
#     a = await send_tx(session, "evmos1u75yzpedd90wp0rqmxa6cz9qnwxa6g0ldp5k6l", "aevmos", "100")
#     return ""

# a = asyncio.run(test())