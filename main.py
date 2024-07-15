import random
import time

from config import *
from classes import *

def main():
    private_keys = Client.get_list_from_file("private_keys.txt")

    if not private_keys:
        logger.error("No private keys found")
        return

    if not lineascan_api_key:
        logger.error("No etherscan api key found")
        return

    if is_shuffle_wallets:
        random.shuffle(private_keys)

    message = ("Выбери какой квест запустить?\n"
               "16. Минт нфт: W2: ACG\n"
               "17. Минт нфт: W2: Toad the Great\n"
               "19. Минт нфт: W3: Acendtheend\n"
               "Введите номер квеста и нажмите Enter\n")
    number_quest = input(message)

    if number_quest == "2":
        urls = Client.get_list_from_file("urls.txt")
        if not urls:
            logger.error("No urls found")
            return
        if len(private_keys) > len(urls):
            logger.error("Добавьте больше ссылок на картинки")
            return

    quest = globals().get(f"Quest_{number_quest}")

    for private_key in private_keys:
        client: Client = quest(private_key)
        try:
            logger.info(f"{client.address} start")
            if client.is_minted():
                logger.info(f"{client.address} already minted")
                client.write_result()
                continue

            if client.mint_nft():
                client.write_result()
                time.sleep(random.uniform(*pause))
            else:
                client.write_error()

        except Exception as ex:
            client.write_error()
            logger.error(f"{client.address} error {ex}")


if __name__ == '__main__':
    main()
