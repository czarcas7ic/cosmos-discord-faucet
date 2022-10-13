from asyncio import sleep
from unittest.main import MAIN_EXAMPLES
import aiofiles as aiof
import aiohttp
import discord
import configparser
import logging
import datetime
import sys
import cosmos_api as api
import evmospy.pyevmosaddressconverter as converter
import json
import os
from discord.ext import commands

from dotenv import load_dotenv
load_dotenv()


from mospy.utils import seed_to_private_key

# Turn Down Discord Logging
disc_log = logging.getLogger('discord')
disc_log.setLevel(logging.INFO)

# Configure Logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Load config
c = configparser.ConfigParser()
c.read("config.ini")
FAUCET_EMOJI = "🚰"

VERBOSE_MODE       = str(c["DEFAULT"]["verbose"])
BECH32_HRP         = str(c["CHAIN"]["BECH32_HRP"])
MAIN_DENOM         = str(c["CHAIN"]["denomination"])
DECIMAL            = float(c["CHAIN"]["decimal"])
DENOMINATION_LST   = c["TX"]["denomination_list"].split(",")
AMOUNT_TO_SEND     = c["TX"]["amount_to_send"]
FAUCET_ADDRESS     = str(c["FAUCET"]["faucet_address"])
FAUCET_MULTISIG_ADDRESS     = str(c["FAUCET"]["faucet_multisig_address"])
EXPLORER_URL       = str(c["OPTIONAL"]["explorer_url"])
if EXPLORER_URL != "":
    EXPLORER_URL = f'{EXPLORER_URL}'
REQUEST_TIMEOUT    = int(c["FAUCET"]["request_timeout"])
TOKEN              = os.getenv("TOKEN")
LISTENING_CHANNELS = str(c["FAUCET"]["channels_to_listen"])
MIN_VALUE          = float(c["OPTIONAL"]["min_dollar_value_threshold"])

APPROVE_EMOJI = "✅"
REJECT_EMOJI = "🚫"
ACTIVE_REQUESTS = {}
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(intents=discord.Intents.all() , command_prefix= "$" , description='Funded by the community for the community')


with open("info-msg.txt", "r", encoding="utf-8") as help_file:
    help_msg = help_file.read()

##FUNCTION
async def save_transaction_statistics(some_string: str):
    # with open("transactions.csv", "a") as csv_file:
    async with aiof.open("transactions.csv", "a") as csv_file:
        await csv_file.write(f'{some_string}\n')
        await csv_file.flush()


async def submit_tx_info(session, message, requester, txhash = ""):
    if message.content.startswith('$tx_info') and txhash == "":
        txhash = str(message.content).replace("$tx_info", "").replace(" ", "")
    try:
        if len(txhash) == 64:

            tx = await api.get_transaction_info(session, txhash)
            logger.info(f"requested txhash {txhash} details")
            if "amount" and "fee" in str(tx):
                from_   = tx['tx']['body']['messages'][0]['from_address']
                to_     = tx['tx']['body']['messages'][0]['to_address']
                amount_ = tx['tx']['body']['messages'][0]['amount'][0]['amount']

                tx = f'{APPROVE_EMOJI} - {requester}\n' \
                    f'{await api.aevmos_to_evmos(amount_)} evmos successfully transfered to {to_}' \
                    '```' \
                    f'From:         {from_}\n' \
                    f'To (BECH32):  {to_}\n' \
                    f'To (HEX):     {converter.evmos_to_eth(to_)}\n' \
                    f'Amount:       {await api.aevmos_to_evmos(amount_)} evmos ```' \
                    f'Explorer => {EXPLORER_URL}/txs/{txhash}'

                await message.channel.send(tx)
                await session.close()
            else:
                await message.channel.send(f'{requester}, `{tx}`')
                await session.close()
        else:
            await message.channel.send(f'Incorrect length for tx_hash: {len(txhash)} instead 64')
            await session.close()

    except Exception as e: 
            logger.error(f"Can't get transaction info {e}")
            await message.channel.send(f"Can't get transaction info of your request {message.content}")

async def requester_onchain_requirements(session,address):
    #verify requester balance
    total_value = 0

    requester_balance = await api.get_addr_all_balance(session, address)
    logger.info(requester_balance)

    with open('./config_ibc.json') as f:
        ibc_json = json.load(f)
        f.close()

    
    for r in requester_balance: 
        if r in ibc_json: 
            
            amount = float(requester_balance[r])
            amount = amount/(10**ibc_json[r]["exponent"])
            
            #query coin value
            coingecko_api=f"https://api.coingecko.com/api/v3/simple/price?ids={ibc_json[r]['coingeckoId']}&vs_currencies=usd"
            headers = {"Content-Type": "application/json"}
            async with session.get(url=coingecko_api, headers=headers) as resp:
                data = await resp.json()
            price = data[ibc_json[r]['coingeckoId']]["usd"]
            total_value += amount * price

    logger.info(f"total value is {total_value}")
    if total_value > MIN_VALUE:
        return True
    else: 
        return False


@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')


@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandOnCooldown):
		await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention}\n'
            f'You already executed the request command. As a security measure, users can only request funds all {REQUEST_TIMEOUT/86400} days. \n'
            f'Please retry in {round((error.retry_after/86400), 2)} days. In case of urgency, please reach out to the mods for dust.'
            )


@bot.command(name='balance')
async def balance(ctx):
    session = aiohttp.ClientSession()
    address = str(ctx.message.content).replace("$balance", "").replace(" ", "").lower()
    if address.startswith("0x") and len(address)== 42: 
        address = converter.eth_to_evmos(address)

    if address[:len(BECH32_HRP)] == BECH32_HRP:
        amount = await api.get_addr_evmos_balance(session, address, MAIN_DENOM)
        if float(amount) > 0:
            await ctx.channel.send(
                f'⚖️ - {ctx.author.mention}\nYour current Evmos balance\n'
                f'```{api.coins_dict_to_string({"evmos": amount}, "grid")}```\n'
                f'To check your IBC token balance please open the block explorer: {EXPLORER_URL}/account/{address}')
            await session.close()

        else:
            await ctx.channel.send(f'{ctx.author.mention} your account is not initialized with evmos (balance is empty)')
            await session.close()

@bot.command(name='info')
async def info(ctx):
    session = aiohttp.ClientSession()
    await ctx.send(help_msg)
    await session.close()


@bot.command(name='faucet_status')
async def status(ctx):
    session = aiohttp.ClientSession()
    logger.info(f"status request by {ctx.author.name}")
    try:
        s = await api.get_node_status(session)
        coins = await api.get_addr_all_balance(session, FAUCET_ADDRESS)

        if "node_info" in str(s) and "error" not in str(s):
            s = f'```' \
                        f'Moniker:       {s["result"]["node_info"]["moniker"]}\n' \
                        f'Address:       {FAUCET_ADDRESS}\n' \
                        f'OutOfSync:     {s["result"]["sync_info"]["catching_up"]}\n' \
                        f'Last block:    {s["result"]["sync_info"]["latest_block_height"]}\n\n' \
                        f'Faucet balance:\n{api.coins_dict_to_string(coins, "")}```'
            await ctx.send(s)
            await session.close()

    except Exception as statusErr:
        logger.error(statusErr)


@bot.command(name='faucet_address')
async def faucet_address(ctx):
    session = aiohttp.ClientSession()
    try:
        await ctx.send(
            f'{FAUCET_EMOJI} - **Bot address** \n \n'
            f'The bots active address is: \n'
            f'`{FAUCET_ADDRESS}`\n \n'
            f'The bots reserve multisig address is: \n'
            f'`{FAUCET_MULTISIG_ADDRESS}`\n'
        )         
        await session.close()
    except:
        logging.error("Can't send message $faucet_address. Please report the incident to one of the mods.")

@bot.command(name='tx_info')
async def tx_info(ctx):
    session = aiohttp.ClientSession()
    await submit_tx_info(session, ctx.message, ctx.author.mention)

@commands.cooldown(1, REQUEST_TIMEOUT, commands.BucketType.user)
@bot.command(name='request')
async def request(ctx):
    session = aiohttp.ClientSession()
    requester_address = str(ctx.message.content).replace("$request", "").replace(" ", "").lower()
    if requester_address.startswith("0x") and len(requester_address)== 42: 
        requester_address = converter.eth_to_evmos(requester_address)
    
    faucet_address_length = len(FAUCET_ADDRESS)
    if len(requester_address) != faucet_address_length or requester_address[:len(BECH32_HRP)] != BECH32_HRP:
        await ctx.send(
            f'{ctx.author.mention}, Invalid address format `{requester_address}`\n'
            f'Address length must be equal to {faucet_address_length} and the prefix must be `{BECH32_HRP}`'
            )
        return

    #check if requester holds $50 of ibc funds 
    min_value = await requester_onchain_requirements(session, requester_address)
    if not min_value: 
        await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention}\n'
            f'You must at least have $50 worth of ibc-tokens ready to be converted. Eligible ibc-tokens are the ones participating in the DeFi kickoff:\n'
            f'```ATOM, JUNO, OSMO, axlWBTC, axlUSDC, axlWETH, gWBTC, gUSDC, gWETH```'
            f'Deposit assets first on https://app.evmos.org/assets before requesting conversion fees from the faucet')
        await session.close()
        return

    #check if requester holds already evmos 
    requester_balance = float(await api.get_addr_evmos_balance(session, requester_address, MAIN_DENOM))
    if requester_balance > float(AMOUNT_TO_SEND): 
        await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention} - You already own {float(requester_balance)/(10**18)} Evmos.'
            f'That is enough to pay for the ibc<>erc20 conversion.')
        await session.close()
        return

        
    #check if faucet has enough balance
    faucet_balance = float(await api.get_addr_evmos_balance(session, FAUCET_ADDRESS, MAIN_DENOM))
    amount_to_send_evmos = await api.aevmos_to_evmos(AMOUNT_TO_SEND)
    if faucet_balance < float(amount_to_send_evmos):  
        await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention} \nFaucet ran out of funds. \n'
            f'Please reach out to the mods to fill it up.')
        await session.close()
        return
        
    transaction = await api.send_tx(session, recipient=requester_address, amount=AMOUNT_TO_SEND)

    if "'code': 0" in str(transaction) and "hash" in str(transaction):
        await submit_tx_info(session, ctx.message, ctx.author.mention ,transaction["hash"])
        logger.info("successfully send tx info to discord")

    else:
        await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention}, Can\'t send transaction. Try making another request'
            f'\n{transaction}'
            )
        logger.error(f"Couldn't process tx {transaction}")
            
    now = datetime.datetime.now()
    await save_transaction_statistics(f'{transaction};{now.strftime("%Y-%m-%d %H:%M:%S")}')
    await session.close()

bot.run(TOKEN)
