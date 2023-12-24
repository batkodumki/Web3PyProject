
import json
from typing import Optional


from web3 import Web3
from eth_account.signers.local import LocalAccount
from web3.providers import HTTPProvider


def get_account_from_seed_phrase(web3: Web3, seed: str) -> LocalAccount:
    """This function is not so useful, but you can use it if you only have seed phrase and doesn`t have a private key"""
    account: LocalAccount = web3.eth.account.from_mnemonic(seed)
    return account


def read_from_json(path: str, encoding: Optional[str] = None) -> list | dict:
    with open(path, mode='r', encoding=encoding) as json_file:
        content = json.load(json_file)
    return content


class Client:
    def __init__(self, provider_uri: str, private_key: str):
        self.w3 = Web3(HTTPProvider(endpoint_uri=provider_uri))

        self.__account: LocalAccount = self.w3.eth.account.from_key(private_key)

    def get_token_decimals(self, token_contract_address: str, token_contract_abi: list | dict) -> int | None:
        try:
            with open("config.json", "r") as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            print('Configuration file not found')
            return

        if not (token_contract_address or token_contract_abi):
            return config['network_native_coin_decimals']

        if (not token_contract_address and token_contract_abi) or (not token_contract_abi and token_contract_address):
            raise Exception("You should define both abi and address for contract, or none of them")
        token_contract_address = Web3.to_checksum_address(token_contract_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        return int(token_contract.functions.decimals().call())

    def get_token_balance(self, *, address_to_check: Optional[str] = None, token_contract_address: str | None = None,
                          token_contract_abi: list | dict | None = None):

        if not (token_contract_address or token_contract_abi):
            return self.w3.eth.get_balance(address_to_check if address_to_check else self.address)

        if (not token_contract_address and token_contract_abi) or (not token_contract_abi and token_contract_address):
            raise Exception("You should define both abi and address for contract, or none of them")

        token_contract_address = Web3.to_checksum_address(token_contract_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        return token_contract.functions.balanceOf(
            self.address if not address_to_check else address_to_check).call()

    @property
    def address(self):
        return self.__account.address
