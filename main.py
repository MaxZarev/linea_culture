import random
import time

from web3 import Web3

from config import *
from classes import Client


def main():
    private_keys = Client.get_private_keys()

    if not private_keys:
        logger.error("No private keys found")
        return

    if not etherscan_api_key:
        logger.error("No etherscan api key found")
        return

    if is_shuffle_wallets:
        random.shuffle(private_keys)

    for private_key in private_keys:
        client = Client(private_key)
        logger.info(f"{client.address} start")
        if client.is_minted():
            logger.info(f"{client.address} already minted")
            client.write_result()
            continue

        if client.mint_nft():
            client.write_result()
            time.sleep(random.randint(*pause))


if __name__ == '__main__':
    main()
