from web3 import Web3
from eth_account.signers.local import LocalAccount


def get_account_from_seed_phrase(web3: Web3, seed: str) -> LocalAccount:
    account: LocalAccount = web3.eth.account.from_mnemonic(seed)
    return account