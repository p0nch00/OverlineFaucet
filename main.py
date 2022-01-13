from datetime import datetime

from discord.ext import commands
from discord.ext.commands import BadArgument, MissingRequiredArgument, CommandInvokeError, MissingRole

import faucet
import secrets
import user_db
from faucet import valid_address

from logger import log, audit_log, raw_audit_log

token = secrets.DISCORD_TOKEN
bot = commands.Bot(command_prefix='faucet-')

def thanks(addr):
    return "If you found this faucet helpful, please consider returning funds to '" \
                  + addr + "`. It will help keep the faucet running. Thank you!"

@bot.event
async def on_ready():
    log(f'Logged in as {bot.user} (ID: {bot.user.id})')
    log('------')


@bot.command(name='send', help='usage: faucet-send  [address]  [tokens (default 0.01)]')
@commands.has_any_role(secrets.MEMBER_DISCORD_ROLE, "Member", "Admin")
async def mainnet_faucet(ctx, address: str, tokens=0.01):
    audit_log(str(ctx.author), str(ctx.author.id), address, tokens)
    guild = str(ctx.guild)
    faucet_address, x = secrets.get_guild_wallet(guild)
    x=""
    # if user's token request is not between 0.04 and 0.001, deny
    if tokens > 0.03:
        response = "Please only request up to 0.03 Matic at a time."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too many tokens.")

    elif tokens < 0.001:
        response = "Please request at least 0.001 Matic."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) +
                      ") requested too few tokens.")

    # if the address's balance already has 0.05 Matic, deny
    elif faucet.get_balance(address) > 0.03:
        response = "Address has greater than 0.03 Matic."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") already has " +
                      str(faucet.get_balance(guild)) + " tokens in their wallet.")

    # if the user or address has already received > 0.03 Matic, deny
    elif user_db.get_user_totals(ctx.author.id, address) >= 0.03:
    # elif user_info.get_user_faucet_total(ctx.author.id) >= 0.03 or user_info.get_address_faucet_total(address) >= 0.03:
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
        response = "Address has 0 transactions. cc:<@712863455467667526>."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") has 0 transactions.")

    # if the faucet does not have enough funds, deny
    elif faucet.get_balance(guild) < (tokens + 0.05):
        response = "The faucet does not have enough funds. Please refill. \n" \
                   "`" + faucet_address + "`"
        raw_audit_log(str(datetime.now()) + ": The faucet is out of funds.")

    # if we passed all the above checks, proceed
    else:
        await ctx.send("The transaction has started and can take up to 2 minutes. Please wait until " +
                       "confirmation before requesting more.")

        success = faucet.send_faucet_transaction(guild, address, tokens)

        # success = True
        if success:
            user_db.add_user(str(ctx.author.id), str(ctx.author))
            user_db.add_transaction(str(ctx.author.id), address, tokens, datetime.now().strftime("%m/%d/%Y, %H:%M:%S"))
            faucet_balance = faucet.get_balance(guild)
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
@commands.has_role(secrets.ADMIN_DISCORD_ROLE)
async def mainnet_faucet_override(ctx, address: str, tokens: float):
    log('mainnet_faucet_override called')
    guild = str(ctx.guild)

    # if we have a good address
    if valid_address(address):

        if faucet.get_balance(guild) > (tokens + 0.01):
            success = faucet.send_faucet_transaction(guild, address, tokens)
            if success:
                response = "**Sent " + str(tokens) + " Matic to " + \
                           address[:4] + "..." + address[-2:] + ". **"
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
        await ctx.send("Role '" + secrets.MEMBER_DISCORD_ROLE + "' is required to run this command.")
        raise error
    else:
        raise error


@bot.command(name='balance', help='usage: faucet-balance')
@commands.has_any_role(secrets.MEMBER_DISCORD_ROLE, "Member", "Admin")
async def get_mainnet_balance(ctx):
    guild = str(ctx.guild)
    faucet_address, x = secrets.get_guild_wallet(guild)
    x = ""
    try:
        balance = faucet.get_balance(guild)
        response = "The faucet has " + str(balance) + " Matic. \n" \
                   "To contribute, you can send Matic to `" + faucet_address + "`."
        raw_audit_log(str(datetime.now()) + ": " + str(ctx.author) + "(" + str(ctx.author.id) + ") checked the balance.")
        await ctx.send(response)
    except Exception as e:
        print(e)


@bot.command(name='mumbai', help='usage: faucet-mumbai [address] [tokens]')
@commands.has_role(secrets.ADMIN_DISCORD_ROLE)
async def mumbai_faucet(ctx, address: str, tokens=1.0):
    log("Mumbai-faucet called")
    guild = str(ctx.guild)

    if valid_address(address):
        if faucet.get_balance(guild) > tokens:
            faucet.send_mumbai_faucet_transaction(guild, address, tokens)
            response = "Sending " + str(tokens) + " test Matic to " + \
                       address[:4] + "..." + address[-2:] + "."
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
@commands.has_role(secrets.ADMIN_DISCORD_ROLE)
async def get_mumbai_balance(ctx):
    guild = str(ctx.guild)

    try:
        balance = faucet.get_mumbai_balance(guild)
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

# @bot.event
# async def on_message(message):
#     # this line handles the case for the bot itself
#     if message.author == bot.user:
#         return
#
#     # checks to see if the message starts with a bot command containing that would contain an address
#     cmds = ['faucet-send', 'faucet-mumbai']
#     if message.content.split(" ")[0] in cmds and valid_address(message.content.split(" ")[1]):
#         # Necessary to also listen for commands
#         await bot.process_commands(message)
#         sleep(2)
#         await message.delete()
#         log("Message deleted")
#
#     else:
#         # Necessary to also listen for commands
#         await bot.process_commands(message)
