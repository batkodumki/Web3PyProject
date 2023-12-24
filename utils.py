import json
from decimal import Decimal
from typing import Optional, Union

from eth_typing import HexStr, ChecksumAddress
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


class TokenAmount:
    amount_in_wei: int
    amount_in_tokens: Decimal
    token_decimals: int

    def __init__(self, amount: Union[int, float, str, Decimal], decimals: int=18, wei:bool = False):
        if wei:
            self.amount_in_wei = amount
            self.amount_in_tokens = Decimal(str(amount)) / 10**decimals
        else:
            self.amount_in_wei = int(Decimal(str(amount))*10**decimals)
            self.amount_in_tokens = Decimal(str(amount))

        self.token_decimals = decimals


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

    def send_transaction(self, address_to: str | ChecksumAddress, data: HexStr | None = None, address_from=None, increase_gas=1.1, value=None):

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
            return None

        signed_transaction = self.__account.sign_transaction(transaction_params)
        transaction_hash = Web3.to_hex(self.w3.eth.send_transaction(signed_transaction.rawTransaction))
        return transaction_hash

    def verify_transaction(self, transaction_hash) -> bool:
        try:
            data = self.w3.eth.wait_for_transaction_receipt(transaction_hash, timeout=180)
            if 'status' in data and data['status'] == 1:
                print(f'{self.address} | transaction was successful: {transaction_hash}')
                return True
            else:
                print(f'{self.address} | transaction failed:{transaction_hash}')
                return False
        except Exception as error:
            print(f'{self.address} | unexpected error in <verify_transaction> function: {error}')
            return False

    def approve(self, token_contract_address, token_contract_abi, spender_address):
        token_contract_address = Web3.to_checksum_address(token_contract_address)
        token_contract = self.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        spender_address = Web3.to_checksum_address(spender_address)
        transaction_hash = self.send_transaction(address_to=token_contract_address, data=token_contract.encodeABI('approve', args=(spender_address,)))