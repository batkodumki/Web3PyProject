from eth_typing import ChecksumAddress
from web3 import Web3

from utils import Client, read_from_json, TokenAmount


class Woofi:
    ROUTER_CONTRACT_ADDRESS = Web3.to_checksum_address("0x9aEd3A8896A85FE9a8CAc52C9B402D092B629a30")
    ROUTER_CONTRACT_ABI = read_from_json("abis/Arbitrum_One/Woofi_ARB_ABI.json")

    def __init__(self, client: Client, router_contract_address: str | ChecksumAddress | None = None, router_contract_abi_filename: str | None = None):
        self.client = client
        if router_contract_address:
            self.ROUTER_CONTRACT_ADDRESS = Web3.to_checksum_address(router_contract_address)
            if not router_contract_abi_filename:
                raise Exception("If you define router's contract address in this network, you should also define router's contract abi")
            self.ROUTER_CONTRACT_ABI = read_from_json(f'abis/{router_contract_abi_filename}')

    def swap_native_token_to_another_token(self, token_contract_address, token_contract_abi, amount: TokenAmount,
                                   slippage: float = 1):
        token_contract = self.client.w3.eth.contract(token_contract_address, abi=token_contract_abi)
        token_decimals = token_contract.functions.decimals().call()
        token_symbol = token_contract.functions.symbol().call()
        router_contract = self.client.w3.eth.contract(self.ROUTER_CONTRACT_ADDRESS, abi=self.ROUTER_CONTRACT_ABI)
        native_token_price_to_token = self.client.get_token_price(self.client.current_token_symbol, token_symbol)

        min_to_amount = TokenAmount(
            amount=native_token_price_to_token * float(amount.amount_in_tokens) * (1 - slippage / 100),
            decimals=token_decimals
        )
        return self.client.send_transaction(address_to=Woofi.ROUTER_CONTRACT_ADDRESS,
                                            data=router_contract.encodeABI('swap', args=(
                                                self.client.current_token_contract_address,
                                                token_contract_address,
                                                amount.amount_in_wei,
                                                min_to_amount.amount_in_wei,
                                                self.client.address,
                                                self.client.address
                                            )), value=amount.amount_in_wei)

    def swap_token_to_another_token(self, first_token_contract_address: str | ChecksumAddress, first_token_contract_abi_filename:str,
                                    second_token_contract_address: str | ChecksumAddress, second_token_contract_abi, amount: float,
                                    slippage: int = 1):
        self.client.change_current_token(first_token_contract_address, first_token_contract_abi)

        first_token_contract_address = self.client.current_token_contract_address
        first_token_symbol = self.client.get_current_token_symbol()
        first_token_amount = TokenAmount(amount, decimals=self.client.get_current_token_decimals())

        self.client.change_current_token(second_token_contract_address, second_token_contract_abi)

        second_token_contract_address = self.client.current_token_contract_address
        second_token_symbol = self.client.get_current_token_symbol()

        first_token_to_second_price = self.client.get_token_price(first_token_symbol, second_token_symbol)
        second_token_amount = TokenAmount(first_token_to_second_price*float(first_token_amount.amount_in_wei)*(1-slippage/100), decimals=self.client.get_current_token_decimals())

        self.client.change_current_token()

        router_contract = self.client.w3.eth.contract(self.ROUTER_CONTRACT_ADDRESS, abi=self.ROUTER_CONTRACT_ABI)
        transaction_hash = self.client.send_transaction(address_to=self.ROUTER_CONTRACT_ADDRESS,
                                                        data=router_contract.encodeABI('swap',
                                                                                         args=(
                                                                                             first_token_contract_address,
                                                                                             second_token_contract_address,
                                                                                             first_token_amount.amount_in_wei,
                                                                                             second_token_amount.amount_in_wei,
                                                                                             self.client.address,
                                                                                             self.client.address
                                                                                         )), value=first_token_amount.amount_in_wei)

        self.client.verify_transaction()
