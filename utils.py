import json
from typing import Optional


from web3 import Web3
from eth_account.signers.local import LocalAccount


def get_account_from_seed_phrase(web3: Web3, seed: str) -> LocalAccount:
    """This function is not so useful, but you can use it if you only have seed phrase and doesn`t have a private key"""
    account: LocalAccount = web3.eth.account.from_mnemonic(seed)
    return account


def read_from_json(path: str, encoding: Optional[str] = None) -> list | dict:
    with open(path, mode='r', encoding=encoding) as json_file:
        content = json.load(json_file)
    return content