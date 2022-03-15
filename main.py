from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import BadArgument, MissingRequiredArgument, CommandInvokeError, MissingRole, MissingAnyRole

import faucet
import secrets
import user_db
from faucet import valid_address

from logger import log, audit_log, raw_audit_log

token = secrets.DISCORD_TOKEN

bot = commands.Bot(command_prefix='faucet-')

def thanks(addr):
    return "If you found this faucet helpful, please consider returning funds to `" \
                  + addr + "`. It will help keep the faucet running. Thank you!"

@bot.event
async def on_ready():
    log(f'Logged in as {bot.user} (ID: {bot.user.id})')
    log('--------')

@bot.command(name='version', help='usage: faucet-version')
@commands.has_any_role(*secrets.ADMIN_DISCORD_ROLES)
async def mainnet_faucet(ctx):
    await ctx.send('v1.0.0')

@bot.command(name='send', help='usage: faucet-send  [address] [tokens]')
@commands.has_any_role(*secrets.MEMBER_DISCORD_ROLES)
async def mainnet_faucet(ctx, address: str, tokens=0.01):
    # tokens = 0.01
    audit_log(str(ctx.author), str(ctx.author.id), address, tokens)
    faucet_address, x = secrets.get_guild_wallet()
    x=""
    user_db.check_if_blacklisted(ctx.author.id, address)

    # if user's token request is not between 0.04 and 0.001, deny
    if tokens > secrets.MAX_TOKENS_REQUESTED:
        response = "Please only request up to " + str(secrets.MAX_TOKENS_REQUESTED) + " Matic at a time."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too many tokens.")

    elif tokens < 0.001:
        response = "Please request at least 0.001 Matic."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too few tokens.")

    # if the address's balance already has enough Matic, deny
    elif faucet.get_balance(address) >= secrets.MAX_TOKENS_REQUESTED:
        response = "Address has greater than " + str(secrets.MAX_TOKENS_REQUESTED) + " Matic."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") already has " +
                      str(faucet.get_faucet_balance()) + " tokens in their wallet.")

    # if the user or address has already received > 0.03 Matic, deny
    elif user_db.get_user_totals(ctx.author.id, address, "Mainnet") >= secrets.MAX_TOKENS_REQUESTED:
        log(str(tokens) + " excess tokens requested by " + str(ctx.author.id) + " author and " + str(
            address) + " address.")
        response = "You have already requested the maximum allowed."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too many tokens.")

    # if we do not have a good address
    elif not valid_address(address):
        response = "usage: `faucet  send [address] [tokens]`. \n" \
                   "Please enter a valid address."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") has an invalid address.")

    # if the address has 0 transactions, deny
    elif not user_db.get_if_existing_account(address):
        response = "Addresses are required to have funds in the wallet to request."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") has 0 transactions.")

    # if the faucet does not have enough funds, deny
    elif faucet.get_faucet_balance() < (tokens + secrets.MAX_TOKENS_REQUESTED):
        response = "The faucet does not have enough funds. Please refill. \n" \
                   "`" + faucet_address + "`"
        raw_audit_log(str(datetime.now()) + ": The faucet is out of funds.")

    elif address == address.lower():
        response = "Your address appears to be in the wrong format. Please make sure your address has both upper- " \
                   "and lower-case letters. This can be found on Polygonscan, or your wallet."
        raw_audit_log(str(datetime.now()) + ": "+address+" was in the wrong format.")

    elif user_db.check_if_blacklisted(ctx.author.id, address):
        response = "Something went wrong. cc:<@712863455467667526>"
        raw_audit_log(str(datetime.now()) + ": " + address + " is on the blacklist.")

    # if we passed all the above checks, proceed
    else:
        await ctx.send("The transaction has started and can take up to 2 minutes. Please wait until " +
                       "confirmation before requesting more.")

        success = faucet.send_faucet_transaction(address, tokens)

        # success = True
        if success:
            user_db.add_user(str(ctx.author.id), str(ctx.author))
            user_db.add_transaction(str(ctx.author.id), address, tokens, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), "Mainnet")
            faucet_balance = faucet.get_faucet_balance()
            response = "**Sent " + str(tokens) + " Matic to " + address[:6] + "..." + \
                       address[-4:] + ".** The faucet now has " + str(faucet_balance) + " Matic left. \n" + \
                       thanks(faucet_address)

        else:
            response = "The bot cannot confirm the transaction went through, please check on Polygonscan. " \
                       "If still not received, try again. cc:<@712863455467667526>"

    # embed = discord.Embed()
    # embed.description = response
    await ctx.send(response)


@bot.command(name='override', help='usage: faucet-override [address] [tokens]')
@commands.has_any_role(*secrets.ADMIN_DISCORD_ROLES)
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
                response = "**Sent " + str(tokens) + " Matic to " + address[:4] + "..." + address[-2:] +  \
                            ". **The faucet now has " + str(faucet.get_faucet_balance()) + " Matic left."
            else:
                response = "There was an error and <@712863455467667526> has been notified."
        else:
            response = "The faucet does not have enough funds. Please refill. \n" \
                       "`0xD8a3dfCae8348E6C52b929c8E50217AD7e4cCa68`"
    else:
        response = "usage: `faucet  send  [address]  [tokens]`. \n" \
                   "Please enter a valid address."
    await ctx.send(response)


@mainnet_faucet.error
async def mainnet_faucet_error(ctx, error):
    if isinstance(error, CommandInvokeError):
        await ctx.send("There was error that <@712863455467667526> needs to fix. Please try again later.")
        raise error
    elif isinstance(error, BadArgument):
        await ctx.send("usage: `faucet-send  [address]`. \n"
                       "Please enter a valid address.")
        raise error
    elif isinstance(error, MissingRequiredArgument):
        await ctx.send("usage: `faucet-send  [address]`")
        raise error
    elif isinstance(error, MissingRole):
        await ctx.send("Role '" + secrets.MEMBER_DISCORD_ROLES + "' is required to run this command.")
        raise error
    else:
        raise error


@bot.command(name='balance', help='usage: faucet-balance')
@commands.has_any_role(*secrets.MEMBER_DISCORD_ROLES)
async def get_mainnet_balance(ctx):
    faucet_address, x = secrets.get_guild_wallet()
    x = ""
    try:
        balance = faucet.get_faucet_balance()
        response = "The faucet has " + str(balance) + " Matic. \n" \
                   "To contribute, you can send Matic to `" + faucet_address + "`."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") checked the balance.")
        await ctx.send(response)
    except Exception as e:
        log(e)


@bot.command(name='blacklist', help='usage: faucet-blacklist [address]')
@commands.has_any_role(*secrets.ADMIN_DISCORD_ROLES)
async def blacklist_address(ctx, address: str):
    await ctx.send(user_db.add_blacklisted_address(ctx.author.id, address))
    log(address + " blacklisted.")
    return


@bot.command(name='mumbai', help='usage: faucet-mumbai [address] [tokens]')
@commands.has_any_role(*secrets.DEVELOPER_DISCORD_ROLES)
async def mumbai_faucet(ctx, address: str, tokens=1.0):
    log("Mumbai-faucet called")

    # if user's token request is not between 0.04 and 0.001, deny
    if tokens > secrets.MAX_MUMBAI_TOKENS_REQUESTED:
        response = "Please only request up to " + str(secrets.MAX_MUMBAI_TOKENS_REQUESTED) + " Matic at a time."

    elif address == address.lower():
        response = "Your address appears to be in the wrong format. Please make sure your address has both upper- " \
                   "and lower-case letters. This can be found on Polygonscan, or your wallet."
        raw_audit_log(str(datetime.now()) + ": " + address + " was in the wrong format.")

    elif user_db.check_if_blacklisted(ctx.author.id, address):
        response = "Something went wrong. cc:<@712863455467667526>"
        raw_audit_log(str(datetime.now()) + ": " + address + " is on the blacklist.")

    # if we passed all the above checks, proceed
    elif valid_address(address):

        if faucet.get_mumbai_balance() > tokens:
            # if the user or address has already received > max Matic, deny
            if user_db.get_user_totals(ctx.author.id, address, "Mumbai") >= secrets.MAX_MUMBAI_TOKENS_REQUESTED:
                response = "You have already requested the maximum allowed, dropping down to 0.1 Matic."
                await ctx.send(response)
                tokens = 0.1

            await ctx.send("The transaction has started and can take up to 2 minutes. Please wait until " +
                           "confirmation before requesting more.")

            success = faucet.send_mumbai_faucet_transaction(address, tokens)

            # success = True
            if success:
                user_db.add_transaction(str(ctx.author.id), address, tokens,
                                        datetime.now().strftime("%m/%d/%Y, %H:%M:%S"), "Mumbai")
                faucet_balance = faucet.get_mumbai_balance()
                response = "**Sent " + str(tokens) + " test Matic to " + address[:6] + "..." + \
                           address[-4:] + ".** The faucet now has " + str(faucet_balance) + " test Matic left."

            else:
                response = "The bot cannot confirm the transaction went through, please check on Polygonscan. " \
                           "If still not received, try again. cc:<@712863455467667526>"
        else:
            response = "The faucet does not have enough funds. Please enter a lower amount or add more to " \
                       "`0xD8a3dfCae8348E6C52b929c8E50217AD7e4cCa68`"


    else:
        response = "usage: `faucet-mumbai  [address]  [tokens]`. \n" \
                   "Please enter a valid address."
    log("Mumbai-faucet: " + response)
    await ctx.send(response)
    return


@bot.command(name='mumbai-balance', help='usage: faucet-mumbai-balance')
@commands.has_any_role(*secrets.ADMIN_DISCORD_ROLES)
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
        await ctx.send("usage: `faucet-mumbai  [address]  [tokens]`. \n"
                       "Please make sure `tokens` is a number.")
        raise error
    elif isinstance(error, MissingAnyRole):
        await ctx.send("Role '" + ", ".join(secrets.DEVELOPER_DISCORD_ROLES) + "' is required to run this command.")
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



# @bot.command(name='kick', help='usage: faucet-kick [#]')
# @commands.has_any_role(*secrets.ADMIN_DISCORD_ROLES)
# async def kick_inactive_users(ctx, num: int):
#     i=0
#
#     users = []
#     for user in list(ctx.guild.members):
#         if i == num:
#             break
#
#         elif len(user.roles) <= 1:
#             #print(user)
#             #print(user.roles)
#             users.append(user.name)
#             await ctx.guild.kick(user)
#             if i % 100 == 0:
#                 print(i)
#             i+=1

    #message = "Users without a role: " + str(users)


bot.run(token)