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

    @property
    def address(self):
        return Web3.to_checksum_address(self.__account.address)

    def get_token_decimals(self, token_contract_address: str, token_contract_abi: list | dict) -> int | None:
        try:
            with open("config.json", "r") as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            print('Configuration file not found')
            return

        if not token_contract_address or not token_contract_abi:
            return config['network_native_coin_decimals']

        token_contract_address = Web3.to_checksum_address(token_contract_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        return int(token_contract.functions.decimals().call())

    def get_balance(self, *, token_contract_address: str | None = None,
                    token_contract_abi: list | dict | None = None, address_to_check: Optional[str] = None):

        if not token_contract_address or not token_contract_abi:
            return self.w3.eth.get_balance(address_to_check if address_to_check else self.address)

        token_contract_address = Web3.to_checksum_address(token_contract_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        return token_contract.functions.balanceOf(
            self.address if not address_to_check else Web3.to_checksum_address(address_to_check)).call()

    def get_allowance(self, token_contract_address: str | None = None, token_contract_abi: list | dict | None = None, owner_address:Optional[str] = None, spender_address: Optional[str] = None):
        if not (token_contract_address and token_contract_abi):
            raise Exception("You should define abi and address of contract")
        token_contract_address = Web3.to_checksum_address(token_contract_address)
        owner_address = self.address if not owner_address else Web3.to_checksum_address(owner_address)
        spender_address = self.address if not spender_address else Web3.to_checksum_address(spender_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        return token_contract.functions.allowance(owner_address, spender_address).call()

    def send_transaction(self, address_to, data=None, address_from=None, increase_gas=1.1, value=None):

        address_from = self.address if not address_from else Web3.to_checksum_address(address_from)
        address_to = Web3.to_checksum_address(address_to)
        gas_price = self.w3.eth.gas_price
        if gas_price > Web3.to_wei(0.1, 'gwei'):
            return
        transaction_params = {
            'chainId': self.w3.eth.chain_id,
            'nonce': self.w3.eth.get_transaction_count(address_from),
            'from': address_from,
            'to': address_to,
            'gasPrice': self.w3.eth.gas_price
        }
        if data:
            transaction_params['data'] = data
        if value:
            transaction_params['value'] = value
        try:
            transaction_params['gas'] = int(self.w3.eth.estimate_gas(transaction_params)*increase_gas)
        except Exception as error:
            print(f"{address_from} | Transaction failed | {error}")
