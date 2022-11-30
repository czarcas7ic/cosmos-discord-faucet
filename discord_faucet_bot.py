from asyncio import sleep
import aiofiles as aiof
import aiohttp
import discord
from cosmospy import privkey_to_address, seed_to_privkey
import configparser
import logging
import time
import datetime
import sys
import cosmos_api as api
from discord.ext import commands

# Turn Down Discord Logging
disc_log = logging.getLogger('discord')
disc_log.setLevel(logging.CRITICAL)

# Configure Logging
logging.basicConfig(stream=sys.stdout, level=logging.CRITICAL)
logger = logging.getLogger(__name__)

# Load config
c = configparser.ConfigParser()
c.read("config.ini")

VERBOSE_MODE       = str(c["DEFAULT"]["verbose"])
BECH32_HRP         = str(c["CHAIN"]["BECH32_HRP"])
DECIMAL            = float(c["CHAIN"]["decimal"])
DENOMINATION_LST   = c["TX"]["denomination_list"].split(",")
AMOUNT_TO_SEND              = c["TX"]["amount_to_send"]
FAUCET_SEED        = str(c["FAUCET"]["seed"])
FAUCET_PRIVKEY     = str(c["FAUCET"]["private_key"])
if FAUCET_PRIVKEY == "":
    FAUCET_PRIVKEY = str(seed_to_privkey(FAUCET_SEED).hex())
FAUCET_ADDRESS     = str(c["FAUCET"]["faucet_address"])
EXPLORER_URL       = str(c["OPTIONAL"]["explorer_url"])
if EXPLORER_URL != "":
    EXPLORER_URL = f'{EXPLORER_URL}/transactions/'
REQUEST_TIMEOUT    = int(c["FAUCET"]["request_timeout"])
TOKEN              = str(c["FAUCET"]["discord_bot_token"])
LISTENING_CHANNELS = list(c["FAUCET"]["channels_to_listen"].split(","))

FAUCET_EMOJI = "🚰"
APPROVE_EMOJI = "✅"
REJECT_EMOJI = "🚫"
ACTIVE_REQUESTS = {}
intents = discord.Intents(messages=True, guilds=True, message_content=True)
bot = commands.Bot(intents=intents,
                   command_prefix="$",
                   description='Funded by the community for the community')

with open("help-msg.txt", "r", encoding="utf-8") as help_file:
    help_msg = help_file.read()


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

                tx = f'🚀 - {requester}\n' \
                     f'{amount_} ulava successfully transfered to {to_}' \
                     '```' \
                     f'From:         {from_}\n' \
                     f'To (BECH32):  {to_}\n' \
                     f'Amount:       {amount_} ulava ```' \
                     f'{EXPLORER_URL}/txs/{txhash}'
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


async def requester_basic_requirements(session, ctx, address, amount):
    faucet_address_length = len(FAUCET_ADDRESS)
    if len(address) != faucet_address_length or address[:len(BECH32_HRP)] != BECH32_HRP:
        await ctx.send(
            f'{ctx.author.mention}, Invalid address format `{address}`\n'
            f'Address length must be equal to {faucet_address_length} and the prefix must be `{BECH32_HRP}`'
        )
        return False

    #check if requester holds already evmos
    requester_balance = float(await api.get_addr_balance(session, address))
    if requester_balance > float(amount):
        await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention} \nYou already own {round(requester_balance,2)} ulava - please use your funds!'
        )
        await session.close()
        return False

    #check if faucet has enough balance
    faucet_balance = float(await api.get_addr_balance(session, FAUCET_ADDRESS))
    if faucet_balance < float(amount):
        await ctx.send(
            f'{REJECT_EMOJI} - {ctx.author.mention} \nFaucet ran out of funds. \n'
            f'Please reach out to the mods to fill it up.')
        await session.close()
        return False


async def eval_transaction(session, ctx, transaction):
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


@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}')


@bot.command(name='faucet_address')
async def faucet_address(ctx):
    session = aiohttp.ClientSession()
    try:
        await ctx.send(
            f'{FAUCET_EMOJI} - **Bot address** \n \n'
            f'The bots active address is: \n'
            f'`{FAUCET_ADDRESS}`\n \n'
        )
        await session.close()
    except:
        logging.error("Can't send message $faucet_address. Please report the incident to one of the mods.")


@bot.command(name='balance')
async def balance(ctx):
    session = aiohttp.ClientSession()
    address = str(ctx.message.content).replace("$balance", "").replace(" ", "").lower()
    logging.info("got balance request", address)
    if address[:len(BECH32_HRP)] == BECH32_HRP:
        coins = await api.get_addr_balance(session, address)
        if float(coins) > 0:
            await ctx.channel.send(
                f'⚖️ - {ctx.author.mention}\nYour current Lava balance\n'
                f'```{api.coins_dict_to_string({"ulava": coins}, "grid")}```\n'
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


@bot.command(name='tx_info')
async def tx_info(ctx):
    session = aiohttp.ClientSession()
    await submit_tx_info(session, ctx.message, ctx.author.mention)


#@commands.cooldown(1, REQUEST_TIMEOUT, commands.BucketType.user)
@bot.command(name='request')
async def request(ctx):
    session = aiohttp.ClientSession()
    requester_address = str(ctx.message.content).replace("$request", "").replace(" ", "").lower()

    #do basic requirements
    basic_checks = await requester_basic_requirements(session, ctx, requester_address, AMOUNT_TO_SEND)
    if basic_checks == False:
        return

    #send and evaluate tx
    transaction = await api.send_tx(session, recipient=requester_address, amount=AMOUNT_TO_SEND)
    await eval_transaction(session, ctx, transaction)


bot.run(TOKEN)
