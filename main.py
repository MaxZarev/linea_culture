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
               "2. Минт нфт день 2: W1:Crazy Gang\n"
               "3. Минт нфт день 3: W1:Push\n"
               "4. Минт нфт день 4: W1:Wizards of Linea\n"
               "5. Минт нфт день 5: W1:eFrogs\n"
               "6. Минт нфт день 6: W2: Satoshi Universe\n"
               "7. Минт нфт день 7: W2: Linus\n"
               "8. Минт нфт день 8: W2: Yooldo\n"
               "9. Минт нфт день 9: W2: Frog Wars\n"
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
