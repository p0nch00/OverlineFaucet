import secrets
from datetime import datetime

import logging
#from systemd.journal import JournalHandler
#log = logging.getLogger('faucet')
#log.addHandler(JournalHandler())
#log.setLevel(logging.INFO)

#def log(message):
#    if secrets.environment == 'test':
#        print(message)
#
#    else:
#        log = logging.getLogger('faucet')
#        log.setLevel(logging.INFO)
#        log.info(message)


def log(message):
    print(message)


def audit_log(user_name: str, user_id: str, address: str, tokens: float):
    f = open(secrets.AUDIT_LOG, "a")
    audit = str(datetime.now()) + ": " + user_name + "(" + user_id + ") requested " + str(tokens) + " to " + address
    f.write(audit)
    f.write('\n')
    f.close()


def raw_audit_log(message: str):
    f = open(secrets.AUDIT_LOG, "a")
    f.write(message)
    f.write('\n')
    f.close()
