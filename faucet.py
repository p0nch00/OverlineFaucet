import json
import re
import configparser
from datetime import datetime, time

import requests as requests

from logger import log, raw_audit_log
#from web3 import Web3

# Load config
c = configparser.ConfigParser()
c.read("config.ini", encoding='utf-8')

FAUCET_ADDRESS = str(c["FAUCET"]["address"])
FAUCET_PRIVKEY = str(c["FAUCET"]["private_key"])
FAUCET_RPC = str(c["RPC"]["mainnet"])

rpc_url = str(c["RPC"]["mainnet"])
#w3 = Web3(Web3.HTTPProvider(rpc_url))

mumbai_rpc_url = rpc_url = str(c["RPC"]["testnet"])
#mumbai_w3 = Web3(Web3.HTTPProvider(mumbai_rpc_url))


def valid_address(address):
    if len(address) == 42 and re.search('0[xX][0-9a-fA-F]{40}', address) and ('[' not in address):
        return True
    return False


# Send a transaction to the requestor
def send_faucet_transaction(address: str, tokens: float):
    headers = {'Content-type': 'application/json', 'Accept': 'application/json', 'authorization': 'Basic OmNvcnJlY3QtaG9yc2UtYmF0dGVyeS1zdGFwbGU='}
    data = {"jsonrpc":"2.0","method":"newTx","params":[FAUCET_ADDRESS, address, str(tokens), "0", FAUCET_PRIVKEY],"id":1}
    print(data)
    reply = requests.post(FAUCET_RPC, data=json.dumps(data), headers=headers)
    rep = json.loads(reply.text)
    result = rep['result']
    resp = result['txHash']
    return str(resp)



# Get address balance
def get_balance(address):
    try:
        headers = {'Content-type': 'application/json', 'Accept': 'application/json',
                   'authorization': 'Basic OmNvcnJlY3QtaG9yc2UtYmF0dGVyeS1zdGFwbGU='}
        data = {"jsonrpc": "2.0", "method": "getBalance", "params": [address], "id": 1}
        print(data)
        r = requests.post(FAUCET_RPC, data=json.dumps(data), headers=headers)
        replydata = r.text
        print(replydata)
        rep = json.loads(replydata)
        resp = rep['result']
        print(resp)
        response = resp['confirmed']
        print(response)
    except Exception as e:
        print(e)
        response = 0.0
    return float(response)


# Get faucet balance
def get_faucet_balance():
    try:
        headers = {'Content-type': 'application/json', 'Accept': 'application/json',
                   'authorization': 'Basic OmNvcnJlY3QtaG9yc2UtYmF0dGVyeS1zdGFwbGU='}
        data = {"jsonrpc": "2.0", "method": "getBalance", "params": [FAUCET_ADDRESS], "id": 1}
        print(data)
        r = requests.post(FAUCET_RPC, data=json.dumps(data), headers=headers)
        replydata = r.text
        print(replydata)
        rep = json.loads(replydata)
        resp = rep['result']
        print(resp)
        response = resp['confirmed']
        print(response)
    except Exception as e:
        print(e)
        response = 0.0
    return float(response)
