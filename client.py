from typing import Optional
import requests


from web3 import Web3
from web3.providers import HTTPProvider
from eth_account.signers.local import LocalAccount


class Client:
    def __init__(self, provider_uri: str, private_key: str):
        self.w3 = Web3(HTTPProvider(endpoint_uri=provider_uri))
        self.account: LocalAccount = self.w3.eth.account.from_key(private_key)

    def get_token_decimals(self, token_contract_address: str, token_contract_abi: list | dict):
        token_contract_address = Web3.to_checksum_address(token_contract_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        return int(token_contract.functions.decimals().call())
