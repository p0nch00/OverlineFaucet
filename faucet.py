import re
from datetime import datetime

import secrets
from logger import log, raw_audit_log
from web3 import Web3


rpc_url = "https://polygon-rpc.com"
w3 = Web3(Web3.HTTPProvider(rpc_url))

#mumbai_rpc_url = "https://rpc-mumbai.maticvigil.com/v1/79315e5d55714f504d1412863718c72c5f344325"
mumbai_rpc_url = "https://rpc-mumbai.maticvigil.com"
mumbai_w3 = Web3(Web3.HTTPProvider(mumbai_rpc_url))


def valid_address(address):
    if len(address) == 42 and re.search('0[xX][0-9a-fA-F]{40}', address) and ('[' not in address):
        return True
    return False


# Send a transaction to the requestor
def send_faucet_transaction(address: str, tokens: float):
    # Get faucet address and faucet's private key from secrets file
    token_from, token_from_private_key = secrets.get_guild_wallet()

    # Token input is in Matic, we need to add the additional 18 decimal places
    tokens = tokens*1e18

    # Get how many transactions we've done to know what our next nonce will be
    nonce = w3.eth.getTransactionCount(token_from)
    log("Trying to send mainnet transaction with nonce " + str(nonce) + "...")

    # Iterate over a few different gas values, with 30 seconds between to make sure it goes through
    for gas in [35*1e9, 50*1e9, 100*1e9, 350*1e9, 500*1e9, 1000*1e9]:
        try:
            log("Trying mainnet transaction to " + address + " with nonce " + str(nonce) + " and gas " + str(gas/1e9))

            # Create the transaction
            signed_txn = w3.eth.account.sign_transaction(dict(
                nonce=nonce,
                gasPrice=int(gas),
                gas=21000,
                to=address,
                value=int(tokens),
                data=b'',
                chainId=137,
            ),
              token_from_private_key,
            )

            # Send the transaction
            txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

            # Wait for confirmation the transaction was mined
            w3.eth.wait_for_transaction_receipt(txn_hash, timeout=30)

            log("Sent mainnet transaction to " + address + " with nonce " + str(nonce))
            raw_audit_log(str(datetime.now()) + ": Sent " + str(tokens) + " Matic to " + str(address) +
                          " with nonce " + str(nonce) + " and gas " + str(gas/1e9))
            return True
        except Exception as e:
            raw_audit_log(str(datetime.now()) + ": Sending failed: " + str(e))
    raw_audit_log(str(datetime.now()) + ": Sending failed.")
    return False


def send_mumbai_faucet_transaction(address: str, tokens: float):
    token_from, token_from_private_key = secrets.get_guild_wallet()

    nonce = mumbai_w3.eth.getTransactionCount(token_from)
    signed_txn = mumbai_w3.eth.account.sign_transaction(dict(
        nonce=nonce,
        gasPrice=25000000000,
        gas=21000,
        to=address,
        value=int(tokens*1e18),
        data=b'',
        chainId=80001,
      ),
      token_from_private_key,
    )

    try:
        # Send the transaction
        txn_hash = mumbai_w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        # Wait for confirmation the transaction was mined
        mumbai_w3.eth.wait_for_transaction_receipt(txn_hash, timeout=30)

        return True
    except Exception as e:
        raw_audit_log(str(datetime.now()) + ": Sending failed: " + str(e))
        return False


# Get address balance
def get_balance(address):

    try:
        response = w3.eth.getBalance(address)/1e18
    except Exception as e:
        print(e)
        response = 0.0
    return response

# Get faucet balance
def get_faucet_balance():
    address, token_from_private_key = secrets.get_guild_wallet()
    try:
        response = w3.eth.getBalance(address)/1e18
    except Exception as e:
        print(e)
        response = 0.0
    return response


def get_mumbai_balance():
    token_from, token_from_private_key = secrets.get_guild_wallet()

    try:
        print(mumbai_w3.eth.getBalance(token_from))
        response = mumbai_w3.eth.getBalance(token_from)/1e18
    except Exception as e:
        response = e
    return response

