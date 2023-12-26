import json
import os
import threading
import time

from dotenv import load_dotenv
from web3 import Web3
from web3.providers import HTTPProvider

from utils import Client
from networks import Networks
import settings


def first_thread_task(web3_client: Client):
    web3_client.fixate_local_account()

    print(web3_client.get_current_token_balance().amount_in_tokens)


def second_thread_task(web3_client: Client):
    web3_client.fixate_local_account()
    print(web3_client.get_current_token_balance().amount_in_tokens)


if __name__ == "__main__":
    load_dotenv()
    client: Client = Client(os.getenv("PRIVATE_KEY"), Networks.BSC)
    threading.Thread(target=first_thread_task, args=(client,)).start()
    threading.Thread(target=second_thread_task, args=(client,)).start()
    time.sleep(0.3)
    client.change_account_globally("ccd2b89b89736f30d47729de094e31e21e771f5000fd46355de366376c316515")
    threading.Thread(target=first_thread_task, args=(client,)).start()
    threading.Thread(target=second_thread_task, args=(client,)).start()
