from datetime import datetime

from discord.ext import commands
from discord.ext.commands import BadArgument, MissingRequiredArgument, CommandInvokeError, MissingRole, MissingAnyRole

import faucet
import user_db
import configparser
import argparse
import json
from faucet import valid_address

from logger import log, audit_log, raw_audit_log

# Load config
c = configparser.ConfigParser()
c.read("config.ini", encoding='utf-8')
argparser = argparse.ArgumentParser()

MAX_TOKENS_REQUESTED = float(c["TOKEN COUNTS"]["MAX_TOKENS_REQUESTED"])
MAX_MUMBAI_TOKENS_REQUESTED = float(c["TOKEN COUNTS"]["MAX_MUMBAI_TOKENS_REQUESTED"])
FAUCET_ADDRESS = str(c["FAUCET"]["address"])
DISCORD_TOKEN = str(c["DISCORD"]["token"])
MEMBER_DISCORD_ROLES = json.loads(c["DISCORD"]["member_roles"])
DEVELOPER_DISCORD_ROLES = json.loads(c["DISCORD"]["developer_roles"])
ADMIN_DISCORD_ROLES = json.loads(c["DISCORD"]["admin_roles"])
#ERROR_MESSAGE_CHANNEL = int(c["DISCORD"]["error_channel"])
DB_CHECK = True if str(c["DATABASE"]["db_check"]).lower() == "true" else False

token = DISCORD_TOKEN

bot = commands.Bot(command_prefix='faucet-')


def thanks(addr):
    return "If you found this faucet helpful, please consider returning funds to `" \
           + addr + "`. It will help keep the faucet running. Thank you!"


@bot.event
async def on_ready():
    log(f'Logged in as {bot.user} (ID: {bot.user.id})')
    log('---------')


@bot.command(name='version', help='usage: faucet-version')
@commands.has_any_role(*ADMIN_DISCORD_ROLES)
async def mainnet_faucet(ctx):
    await ctx.send('v1.6.9')


@bot.command(name='send', help='usage: faucet-send  [address] [coins]')
@commands.has_any_role(*MEMBER_DISCORD_ROLES)
async def mainnet_faucet(ctx, address: str, tokens=0.01):
    # tokens = 0.01
    audit_log(str(ctx.author), str(ctx.author.id), address, tokens)

    # if user's token request is not between 0.04 and 0.001, deny
    if tokens > MAX_TOKENS_REQUESTED:
        response = "Please only request up to " + str(MAX_TOKENS_REQUESTED) + " OL at a time."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too many tokens.")

    # if token request is too small
    elif tokens < 0.001:
        response = "Please request at least 0.001 OL."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too few tokens.")

    # if the address's balance already has enough Matic, deny
    elif faucet.get_balance(address) >= MAX_TOKENS_REQUESTED:
        response = "Address has greater than " + str(MAX_TOKENS_REQUESTED) + " OL."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") already has " +
                      str(faucet.get_faucet_balance()) + " coins in their wallet.")

    # if the user or address has already received > 0.03 Matic, deny
    elif DB_CHECK and (user_db.get_user_totals(ctx.author.id, address, "Mainnet") >= MAX_TOKENS_REQUESTED):
        log(str(tokens) + " excess tokens requested by " + str(ctx.author.id) + " author and " + str(
            address) + " address.")
        response = "You have already requested the maximum allowed."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too many tokens.")

    # if we do not have a good address
    elif not valid_address(address):
        response = "usage: `faucet  send [address] [coins]`. \n" \
                   "Please enter a valid address."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") has an invalid address.")

    # if the address has 0 transactions, deny
    elif not user_db.get_if_existing_account(address):
        response = "Address must have activity/previous transactions before requesting."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") has 0 transactions.")

    # if the faucet does not have enough funds, deny
    elif faucet.get_faucet_balance() < (tokens + MAX_TOKENS_REQUESTED):
        response = "The faucet does not have enough funds. Please refill. \n" \
                   "`" + FAUCET_ADDRESS + "`"
        raw_audit_log(str(datetime.now()) + ": The faucet is out of funds.")

    #elif address == address.lower():
    #    response = "Your address appears to be in the wrong format. Please make sure your address has both upper- " \
    #               "and lower-case letters. This can be found on your wallet."
    #    raw_audit_log(str(datetime.now()) + ": " + address + " was in the wrong format.")

    elif DB_CHECK and user_db.check_if_blacklisted(ctx.author.id, address):
        response = "User blacklisted."
        raw_audit_log(str(datetime.now()) + ": " + address + " is on the blacklist.")

    # if we passed all the above checks, proceed
    else:
        await ctx.send("The transaction has started and can take up to 2 minutes. Please wait until " +
                       "confirmation before requesting more.")

        success = faucet.send_faucet_transaction(address, tokens)

        if success:
            if DB_CHECK:
                user_db.add_user(str(ctx.author.id), str(ctx.author))
                user_db.add_transaction(str(ctx.author.id), address, tokens, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"),
                                        "Mainnet")
            response = "**Sent " + str(tokens) + " OL to " + address[:6] + "..." + \
                       address[-4:] + ".**\n" + \
                       thanks(FAUCET_ADDRESS)

        else:
            response = "The bot cannot confirm the transaction went through, please check on Explorer. " \
                       "If still not received, try again."

    # embed = discord.Embed()
    # embed.description = response
    await ctx.send(response)


@bot.command(name='override', help='usage: faucet-override [address] [tokens]')
@commands.has_any_role(*ADMIN_DISCORD_ROLES)
async def mainnet_faucet_override(ctx, address: str, tokens=0.01):
    print("here")
    log('mainnet_faucet_override called')

    # if we have a good address
    if address == address.lower():
        response = "Your address appears to be in the wrong format. Please make sure your address has both upper- " \
                   "and lower-case letters. This can be found on Polygonscan, or your wallet."
        raw_audit_log(str(datetime.now()) + ": " + address + " was in the wrong format.")

    elif valid_address(address):

        if faucet.get_faucet_balance() > (tokens + 0.01):
            await ctx.send("The transaction has started and can take up to 2 minutes.")

            success = faucet.send_faucet_transaction(address, tokens)
            if success:
                response = "**Sent " + str(tokens) + " OL to " + address[:4] + "..." + address[-2:] + \
                           ". **The faucet now has " + str(faucet.get_faucet_balance()) + " OL left."
            else:
                response = "There was an error, please try again later or alert an admin."
        else:
            response = "The faucet does not have enough funds. Please refill. \n`{FAUCET_ADDRESS}`"
    else:
        response = "usage: `faucet  send  [address]  [tokens]`. \n" \
                   "Please enter a valid address."
    await ctx.send(response)


@mainnet_faucet.error
async def mainnet_faucet_error(ctx, error):
    error_channel = bot.get_channel("debug")
    if str(error) == "Command raised an exception: TypeError: string indices must be integers":
        await ctx.send("usage: `faucet-send  [address]`. \n"
                       "Please do not use brackets when entering an address.")
        await error_channel.send("CommandInvokeError: \n" + str(error))
        raise error
    if isinstance(error, CommandInvokeError):
        await ctx.send("There was error that <@712863455467667526> needs to fix. Please try again later.")
        await error_channel.send("CommandInvokeError: \n" + str(error))
        raise error
    elif isinstance(error, BadArgument):
        await ctx.send("usage: `faucet-send  [address]`. \n"
                       "Please enter a valid address.")
        await error_channel.send("BadArgument: \n" + str(error))
        raise error
    elif isinstance(error, MissingRequiredArgument):
        await ctx.send("usage: `faucet-send  [address]`")
        await error_channel.send("MissingRequiredArgument: \n" + str(error))
        raise error
    elif isinstance(error, MissingAnyRole):
        await ctx.send(
            "You are missing at least one of the required roles: '" + ", ".join(MEMBER_DISCORD_ROLES) + "'.")
        await error_channel.send("MissingRole: \n" + str(error))
        raise error
    else:
        await error_channel.send("Else: \n" + str(error))
        raise error


@bot.command(name='balance', help='usage: faucet-balance')
@commands.has_any_role(*MEMBER_DISCORD_ROLES)
async def get_mainnet_balance(ctx):
    try:
        balance = faucet.get_faucet_balance()
        response = "The faucet has " + str(balance) + " OL. \n" \
                                                      "To contribute, you can send OL to `" + FAUCET_ADDRESS + "`."
        raw_audit_log(
            str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") checked the balance.")
        await ctx.send(response)
    except Exception as e:
        log(e)


@bot.command(name='blacklist', help='usage: faucet-blacklist [address]')
@commands.has_any_role(*ADMIN_DISCORD_ROLES)
async def blacklist_address(ctx, address: str):
    if not DB_CHECK:
        await ctx.send("Database checks not enabled.")
    await ctx.send(user_db.add_blacklisted_address(ctx.author.id, address))
    log(address + " blacklisted.")
    return


@bot.command(name='mumbai', help='usage: faucet-mumbai [address] [tokens]')
@commands.has_any_role(*DEVELOPER_DISCORD_ROLES)
async def mumbai_faucet(ctx, address: str, tokens=MAX_MUMBAI_TOKENS_REQUESTED):
    log("Mumbai-faucet called")

    # if user's requests too many tokens, deny
    if tokens > MAX_MUMBAI_TOKENS_REQUESTED:
        response = "Please only request up to " + str(MAX_MUMBAI_TOKENS_REQUESTED) + " OL at a time."

    elif address == address.lower():
        response = "Your address appears to be in the wrong format. Please make sure your address has both upper- " \
                   "and lower-case letters. This can be found on Polygonscan, or your wallet."
        raw_audit_log(str(datetime.now()) + ": " + address + " was in the wrong format.")

    elif DB_CHECK and user_db.check_if_blacklisted(ctx.author.id, address):
        response = "User blacklisted."
        raw_audit_log(str(datetime.now()) + ": " + address + " is on the blacklist.")

    # if we passed all the above checks, proceed
    elif valid_address(address):

        # if faucet.get_mumbai_balance() > tokens:
        # if the user or address has already received > max Matic, deny
        if DB_CHECK and (user_db.get_user_totals(ctx.author.id, address, "Mumbai") >= MAX_MUMBAI_TOKENS_REQUESTED):
            response = "You have already requested the maximum allowed, dropping down to 0.5 OL."
            await ctx.send(response)
            tokens = 0.5

        await ctx.send("The transaction has started and can take up to 2 minutes. Please wait until " +
                       "confirmation before requesting more.")

        success = faucet.send_mumbai_faucet_transaction(address, tokens)

        # success = True
        if success:
            if DB_CHECK:
                user_db.add_transaction(str(ctx.author.id), address, tokens,
                                    datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), "Mumbai")
            response = "**Sent " + str(tokens) + " test OL to " + address[:6] + "..." + \
                       address[-4:] + ".**"

        else:
            response = "The bot cannot confirm the transaction went through, please check on Polygonscan. " \
                       "If still not received, try again."

    else:
        response = "usage: `faucet-mumbai  [address]  [tokens]`. \n" \
                   "Please enter a valid address."
    log("Mumbai-faucet: " + response)
    await ctx.send(response)
    return


@bot.command(name='mumbai-override', help='usage: faucet-mumbai-override [address] [tokens]')
@commands.has_any_role(*ADMIN_DISCORD_ROLES)
async def mumbai_faucet_override(ctx, address: str, tokens=1):
    print("here")
    log('mumbai_faucet_override called')

    # if we have a good address
    if address == address.lower():
        response = "Your address appears to be in the wrong format. Please make sure your address has both upper- " \
                   "and lower-case letters. This can be found on Polygonscan, or your wallet."
        raw_audit_log(str(datetime.now()) + ": " + address + " was in the wrong format.")

    elif valid_address(address):

        if faucet.get_mumbai_balance() > (tokens + 0.01):
            await ctx.send("The transaction has started and can take up to 2 minutes.")

            success = faucet.send_mumbai_faucet_transaction(address, tokens)
            if success:
                response = "**Sent " + str(tokens) + " OL to " + address[:4] + "..." + address[-2:] + \
                           ". **The faucet now has " + str(faucet.get_faucet_balance()) + " OL left."
            else:
                response = "There was an error."
        else:
            response = f"The faucet does not have enough funds. Please refill.\n`{FAUCET_ADDRESS}`"
    else:
        response = "usage: `faucet  send  [address]  [tokens]`. \n" \
                   "Please enter a valid address."
    await ctx.send(response)


@bot.command(name='mumbai-balance', help='usage: faucet-mumbai-balance')
@commands.has_any_role(*ADMIN_DISCORD_ROLES)
async def get_mumbai_balance(ctx):
    try:
        balance = faucet.get_mumbai_balance()
        response = "The faucet has " + str(balance) + " Maticmum"
        await ctx.send(response)
    except Exception as e:
        log(e)


@mumbai_faucet.error
async def mumbai_faucet_error(ctx, error):
    if isinstance(error, CommandInvokeError):
        await ctx.send("There was an issue, possibly with the RPC.")
        raise error
    elif isinstance(error, MissingAnyRole):
        await ctx.send(
            "You are missing at least one of the required roles: '" + ", ".join(DEVELOPER_DISCORD_ROLES) + "'.")
        raise error
    elif isinstance(error, BadArgument):
        await ctx.send("usage: `faucet-mumbai  [address]  [tokens]`. \n"
                       "Please enter a valid address.")
        raise error
    elif isinstance(error, MissingRequiredArgument):
        await ctx.send("usage: `faucet-mumbai  [address]  [tokens]`")
        raise error
    else:
        log(error)
        raise error


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')


bot.run(token)
