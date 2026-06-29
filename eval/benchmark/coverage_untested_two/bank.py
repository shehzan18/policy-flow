def transfer(acct, amount):
    if amount <= 0:
        raise ValueError
    acct.balance -= amount
    return acct.balance
