import os
import json
from dotenv import load_dotenv
from eth_account.signers.local import LocalAccount

from web3 import Web3
from web3.providers import HTTPProvider


if __name__ == "__main__":
    load_dotenv()
    try:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
            web3 = Web3(HTTPProvider(endpoint_uri=config["http_provider_uri"]))
            print(f"Gas price in {config['network_name']} is {web3.from_wei(web3.eth.gas_price, 'gwei')} GWEI")
            print(f"Current block number in {config['network_name']} is {web3.eth.block_number}")
            print(f"Current chain id is {web3.eth.chain_id}")

            account: LocalAccount = web3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
            balance = Web3.from_wei(web3.eth.get_balance(Web3.to_checksum_address(account.address)),"ether")
            print(f"Balance of account in {config['network_parent_coin_symbol']} is {balance}")
    except FileNotFoundError:
        print('Configuration file not found')
