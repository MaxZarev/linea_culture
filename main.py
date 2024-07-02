import random
import time

from config import *
from classes import Client


def main():
    private_keys = Client.get_list_from_file("data/private_keys.txt")
    urls = Client.get_list_from_file("data/urls.txt")

    if not urls:
        logger.error("No urls found")
        return

    if not private_keys:
        logger.error("No private keys found")
        return

    if not lineascan_api_key:
        logger.error("No etherscan api key found")
        return

    if len(private_keys) > len(urls):
        logger.error("Добавьте больше ссылок на картинки")
        return

    if is_shuffle_wallets:
        random.shuffle(private_keys)

    for private_key in private_keys:
        client = Client(private_key)
        try:
            logger.info(f"{client.address} start")
            if client.is_minted():
                logger.info(f"{client.address} already minted")
                client.write_result()
                continue

            if client.mint_nft():
                client.write_result()

        except Exception as ex:
            logger.error(f"{client.address} error {ex}")

        time.sleep(random.randint(*pause))


if __name__ == '__main__':
    main()
