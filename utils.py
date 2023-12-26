import json
import threading
from decimal import Decimal
from typing import Optional, Union
import requests


from eth_account.signers.local import LocalAccount
from eth_typing import HexStr, ChecksumAddress
from web3 import Web3
from web3.contract import Contract
from web3.providers import HTTPProvider


from networks import Networks
from transactiontypes import TransactionTypes
import settings


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
    amount_in_tokens: Decimal | float
    token_decimals: int

    def __init__(self, amount: Union[int, float, str, Decimal], decimals: int = 18, wei: bool = False):
        if wei:
            self.amount_in_wei = amount
            self.amount_in_tokens = float(amount) / 10 ** decimals
        else:
            self.amount_in_wei = int(amount * 10 ** decimals)
            self.amount_in_tokens = Decimal(str(amount))

        self.token_decimals = decimals


class Client:

    def __init__(self, private_key: str, network: Networks, provider_uri: str | None = None):
        """You can pass provider_uri if you can not connect to node using the provider uri in basic config"""
        try:
            with open(f"{settings.NETWORK_CONFIGS_FOLDER}/{network.value}.json", "r") as config_file:
                self.__config = json.load(config_file)
        except FileNotFoundError:
            raise Exception('Configuration file not found for this network, try to choose another one network')
        self.w3 = Web3(
            HTTPProvider(endpoint_uri=self.__config['http_provider_uri'] if not provider_uri else provider_uri))
        if not self.w3.is_connected():
            raise Exception(
                "Can not connect to network provider. You can search it on ChainList for your network and change it "
                "in network_configs folder for your network")
        self.local = threading.local()
        self.network = network
        self.__account: LocalAccount = self.w3.eth.account.from_key(private_key)
        self.local.account = self.__account
        self.__accounts = {private_key: self.local.account}
        self.chain_id = self.w3.eth.chain_id
        self.__native_token_contract_address = self.__config['native_token_contract_address']
        self.__native_token_decimals = self.__config['native_token_decimals']
        self.__native_token_symbol = self.__config['native_token_symbol']
        self.__current_token_contract: Optional[Contract] = None
        self.__is_current_token_native = True
        self.__native_token_contract_address = Web3.to_checksum_address(self.__config['native_token_contract_address'])
        self.__locks = {private_key: threading.RLock()}

    def change_account_locally(self, private_key: str):
        """Call this function if you want to change an active account locally in your thread"""
        self.local.account = self.w3.eth.account.from_key(private_key)
        self.__locks[private_key] = threading.RLock()

    def change_account_globally(self, private_key: str):
        """Call this function in main thread if you want to change an active account globally (in main thread also).
        Before using it, let another threads that started early to fixate their local account's instances using
        time.sleep(0.1) etc. before calling this function.
        """
        self.__account = self.w3.eth.account.from_key(private_key)
        self.local.account = self.__account

    def fixate_local_account(self):
        """Call this function in thread to fixate a current account instance for this thread
        Should be called at the start of a thread function(it is possible that main thread can change account globally
        during this thread's job and if you call it lately it will fixate a new global account as a local instance)"""
        self.local.account = self.__account

    @property
    def address(self):
        return Web3.to_checksum_address(self.local.account.address)

    def change_current_token(self, token_contract_address: str | ChecksumAddress | None = None,
                             token_contract_abi_filename: str | None = None, native: bool = False):

        if native and (token_contract_address or token_contract_abi_filename):
            print('You can not set native=True and also pass a token contract`s address or abi')
            return

        elif not native and not (token_contract_address and token_contract_abi_filename):
            print('If you set native=False, you must pass both contract`s address and abi')
            return
        else:
            if native:
                self.__current_token_contract = None
                self.__is_current_token_native = True
            else:
                self.__current_token_contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(token_contract_address),
                    abi=read_from_json(f'{settings.ABIS_FOLDER}/{self.network.value}/{token_contract_abi_filename}'))
                self.__is_current_token_native = False

    @property
    def is_current_token_native(self) -> bool:
        return self.__is_current_token_native

    def get_current_token_symbol(self) -> str:
        if self.__is_current_token_native:
            return self.__native_token_symbol
        return self.__current_token_contract.functions.symbol().call()

    def get_current_token_decimals(self) -> int:
        if self.__is_current_token_native:
            return self.__native_token_decimals
        return self.__current_token_contract.functions.decimals().call()

    def get_current_token_balance(self) -> TokenAmount:
        if self.__is_current_token_native:
            balance_in_wei = self.w3.eth.get_balance(self.local.account.address)
            return TokenAmount(balance_in_wei, self.__native_token_decimals, wei=True)
        balance_in_wei = self.__current_token_contract.functions.balanceOf(
            self.local.account.address).call()
        return TokenAmount(balance_in_wei, self.get_current_token_decimals(), wei=True)

    def get_current_token_allowance(self, spender_address: str | ChecksumAddress) -> TokenAmount:

        if self.__is_current_token_native:
            print("Your current token is native, so there is no allowance or approve for it!")
            return TokenAmount(2 ** 256 - 1, decimals=self.__native_token_decimals, wei=True)
        spender_address = Web3.to_checksum_address(spender_address)
        allowance = self.__current_token_contract.functions.allowance(self.address, spender_address).call()
        return TokenAmount(allowance, decimals=self.get_current_token_decimals(), wei=True)

    def send_transaction(self, address_to: str | ChecksumAddress, data: HexStr | None = None,
                         value: float | Decimal | None = None):
        address_to = Web3.to_checksum_address(address_to)
        transaction_params = {
            'chainId': self.chain_id,
            'from': self.address,
            'to': address_to,
            'gasPrice': self.w3.eth.gas_price
        }
        if data:
            transaction_params['data'] = data
        if value:
            value = TokenAmount(value, decimals=self.get_current_token_decimals())
            transaction_params['value'] = value.amount_in_wei
        with self.__locks[self.local.account.private_key]:
            transaction_params['nonce'] = self.w3.eth.get_transaction_count(self.address)
            try:
                transaction_params['gas'] = int(self.w3.eth.estimate_gas(transaction_params))
            except Exception as error:
                print(f"{self.address} | Transaction failed | {error}")
                return None
            signed_transaction = self.local.account.sign_transaction(transaction_params)
            transaction_hash = self.w3.eth.send_raw_transaction(signed_transaction.rawTransaction).hex()
        return transaction_hash

    def verify_transaction(self, transaction_hash, transaction_type: TransactionTypes, timeout: int = 120) -> bool:
        try:
            data = self.w3.eth.wait_for_transaction_receipt(transaction_hash, timeout)
            if 'status' in data and data['status'] == 1:
                print(
                    f'{self.address} | {transaction_type.value} transaction was successful.Transaction hash: {transaction_hash}')
                return True
            else:
                print(
                    f'{self.address} | {transaction_type.value} transaction failed. Transaction hash:{transaction_hash}. Transaction data:{data}')
                return False
        except Exception as error:
            print(
                f'{self.address} | Unexpected error during verification the {transaction_type.value} transaction: {error}')
            return False



    def approve(self, spender_address: str | ChecksumAddress, amount: float | Decimal) -> bool:

        if self.__is_current_token_native:
            print(
                f"{self.address} | Your current token is native, so there is no need in approve for spender {spender_address}")
            return True
        amount_of_tokens_to_approve = TokenAmount(amount, self.get_current_token_decimals())
        if self.get_current_token_allowance(spender_address).amount_in_tokens >= amount:
            print(
                f"{self.address} | Allowance for {spender_address} is already equal or bigger than you want to approve!")
            return True
        spender_address = Web3.to_checksum_address(spender_address)
        transaction_hash = self.send_transaction(address_to=self.__current_token_contract.address,
                                                 data=self.__current_token_contract.encodeABI('approve',
                                                                                              args=(spender_address,
                                                                                                    amount_of_tokens_to_approve.amount_in_wei)))
        if self.verify_transaction(transaction_hash, TransactionTypes.APPROVE):
            return True
        return False

    def send_current_token(self, address_to_send: str | ChecksumAddress, value: float | None = None):
        balance = self.get_current_token_balance()
        if value > balance.amount_in_tokens:
            print(f"{self.address}| Tried to send more than a balance")
            return
        address_to_send = Web3.to_checksum_address(address_to_send)
        amount_to_send = TokenAmount(value, decimals=self.get_current_token_decimals())
        if self.approve(address_to_send, amount_to_send.amount_in_tokens):
            if self.__is_current_token_native:
                transaction_hash = self.send_transaction(address_to_send, value=amount_to_send.amount_in_tokens)
            else:
                transaction_hash = self.send_transaction(self.__current_token_contract.address,
                                                         data=self.__current_token_contract.encodeABI(
                                                             fn_name='transfer',
                                                             args=(address_to_send, amount_to_send.amount_in_wei)))
            self.verify_transaction(transaction_hash, transaction_type=TransactionTypes.SEND)

    @staticmethod
    def get_token_price(first_token_symbol="ETH", second_token_symbol="USDT"):
        first_token = first_token_symbol.upper()
        second_token = second_token_symbol.upper()
        print(f'getting {first_token} price')
        response = requests.get("https://api.binance.com/api/v3/ticker/price",
                                params={'symbol': f'{first_token}{second_token}'})
        if response.status_code != 200:
            print(f'getting {first_token} price to {second_token} did not complete | {response.json()}')
            return None

        return float(response.json()['price'])
