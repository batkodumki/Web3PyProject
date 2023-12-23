import json

from web3 import Web3
from web3.providers import HTTPProvider

if __name__ == "__main__":
    try:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
            web3 = Web3(HTTPProvider(endpoint_uri=config["arbitrum_rpc_uri"]))

    except FileNotFoundError:
        print('Configuration file not found')
