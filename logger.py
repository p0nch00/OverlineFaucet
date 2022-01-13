import secrets
from datetime import datetime

#
# def log(message):
#     if secrets.environment == 'test':
#         print(message)
#
#     else:
#         from systemd import journal
#
#         journal.write(message)


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
