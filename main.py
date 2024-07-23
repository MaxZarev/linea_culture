import random
import time

from config import *
from classes import *

def main():
    logger.warning("Внимание!!! Обратите внимание для 26 квеста нужно заполнить \n"
                   "файл proxy.txt в папке data в формате ip:port:login:password\n"
                   "количество прокси = количество кошельков\n")
    time.sleep(5)
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
               "20. Минт нфт: W3: SendingMe\n"
               "21. Минт нфт: W3: Townstory\n"
               "22. Минт нфт: W3: Danielle Zosavac\n"
               "23. Минт нфт: W3: demmortal\n"
               "24. Минт нфт: W3: foxy\n"
               "26. Минт нфт: w4: coop-records\n"
               "27. Минт нфт: w4: borja-moskv\n"
               "Введите номер квеста и нажмите Enter\n")
    number_quest = input(message)

    if number_quest == "26":
        urls = Client.get_list_from_file("proxy.txt")
        if not urls:
            logger.error("Добавьте список прокси в файл proxy.txt для квеста 26")
            return
        if len(private_keys) > len(urls):
            logger.error("Добавьте больше прокси в файл proxy.txt для квеста 26")
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
