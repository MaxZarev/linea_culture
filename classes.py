import json
import os
import random
import time

import requests
from faker import Faker
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.types import Wei

from config import *


class Client:
    contract_address = ""
    start_block = 6084611  # на случай если ранее были минты по контракту
    proxy: str = None

    def __init__(self, pk: str):
        self.w3 = Web3(Web3.HTTPProvider(RPC))
        self.pk = pk
        self.address = self.w3.eth.account.from_key(pk).address
        self.abi = self.__class__.__name__.lower()

    @staticmethod
    def get_list_from_file(file_name: str) -> list[str]:
        """
        Читает файл и возвращает список строк
        :param path: название файла
        :return:
        """
        os_path = os.path.join("data", file_name)
        with open(os_path, "r") as file:
            return file.read().splitlines()

    def get_contract(self) -> Contract:
        """
        Получает контракт по адресу и аби в заливистости от класса
        :return: инициализированный контракт
        """
        contract_address = self.w3.to_checksum_address(self.contract_address)
        abi = self.get_abi()
        contract = self.w3.eth.contract(address=contract_address, abi=abi)
        return contract

    def check_balance(self):
        balance = self.w3.eth.get_balance(self.address)
        if balance < min_balance / 3500 * 10 ** 18:
            logger.error(f"{self.address} : Not enough balance!")
            return True
        else:
            return False

    def send_transaction(self, transaction: dict, gas: int = 0) -> HexBytes:
        """
        Подписывает транзакцию приватным ключем и отправляет в сеть
        :param transaction: словарь с параметрами транзакции
        :param gas: лимит газа, если не указывать считается автоматически
        :return: хэш транзакции
        """
        if gas:
            transaction['gas'] = gas
        else:
            transaction['gas'] = int((self.w3.eth.estimate_gas(transaction)) * random.uniform(*gas_coef))

        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.pk)

        return self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    def get_abi(self) -> str:
        """
        Читает json файл в папке data
        :return: словарь с abi
        """
        with open(os.path.join("data", "ABIs", f"{self.abi}.json")) as f:
            return json.loads(f.read())

    def prepare_transaction(self, value: Wei = 0) -> dict:
        """
        Подготавливает параметры транзакции, от кого, кому, чейн-ади и параметры газа
        :param value: сумма транзакции, если отправляется ETH или нужно платить, сумма в wei
        :return: словарь с параметрами транзакции
        """
        tx_params = {
            'from': self.address,
            'nonce': self.w3.eth.get_transaction_count(self.address),
            'chainId': self.w3.eth.chain_id,
        }

        if value:
            tx_params['value'] = value

        base_fee = 7

        max_priority_fee_per_gas = self.get_priority_fee()

        max_fee_per_gas = base_fee + max_priority_fee_per_gas

        tx_params['maxPriorityFeePerGas'] = max_priority_fee_per_gas
        tx_params['maxFeePerGas'] = int(max_fee_per_gas * random.uniform(*gas_coef))
        tx_params['type'] = '0x2'
        return tx_params

    def get_proxy(self):
        """
        Получает прокси для конкретного кошелька
        :return: прокси
        """
        proxies = Client.get_list_from_file("proxy.txt")
        private_keys = Client.get_list_from_file("private_keys.txt")

        for i in range(len(private_keys)):
            if private_keys[i] == self.pk:
                return proxies[i]

    def get_priority_fee(self) -> int:
        """
        Получает среднюю цену за приоритетную транзакцию за последние 25 блоков
        :return: средняя цена за приоритетную транзакцию
        """
        fee_history = self.w3.eth.fee_history(25, 'latest', [20.0])
        non_empty_block_priority_fees = [fee[0] for fee in fee_history["reward"] if fee[0] != 0]
        divisor_priority = max(len(non_empty_block_priority_fees), 1)
        priority_fee = int(round(sum(non_empty_block_priority_fees) / divisor_priority))

        return priority_fee

    def is_minted(self) -> bool:
        """
        Проверяет наличие взаимодействия с контрактом, чтобы не было дублирования транзакций
        :param contract_address: адрес смарт-контракта
        :return: возвращает True если взаимодействие было, иначе False
        """
        url = (f"https://api.lineascan.build/api"
               f"?module=account"
               f"&action=txlist"
               f"&address={self.address}"
               f"&startblock={self.start_block}"
               f"&endblock=99999999"
               f"&page=1"
               f"&offset=10000"
               f"&sort=asc"
               f"&apikey={lineascan_api_key}")
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Can't get data from etherscan: {response.text}")
        if response.json()['status'] == "1":
            for tx in response.json()['result']:
                if tx['to'].lower() == self.contract_address.lower() and tx['txreceipt_status'] == "1":
                    return True
        else:
            if response.text.__contains__("No transactions found"):
                return False
            else:
                raise Exception(f"Can't get data from etherscan: {response.text}")

        return False

    def write_result(self) -> None:
        """
        Записывает адрес кошелька в файл data/result.txt в конце файла
        :return: None
        """
        with open(os.path.join("data", "result.txt"), "a") as file:
            file.write(self.address + "\n")

    def write_error(self) -> None:
        """
        Записывает адрес кошелька в файл data/error.txt в конце файла
        :return: None
        """
        with open(os.path.join("data", "error.txt"), "a") as file:
            file.write(self.address + "\n")

    def build_transaction(self, contract: Contract) -> dict:
        pass

    def mint_nft(self) -> bool:
        # проверяем баланс, если нужно

        if is_check_balance:
            if self.check_balance():
                return False

        contract = self.get_contract()

        tx = self.build_transaction(contract)

        tx_hash = self.send_transaction(tx)
        logger.info(f"{self.address} minted: {tx_hash.hex()}")
        return True

    def get_tx_data_from_phosphor(self, listing_id: str) -> tuple[str, tuple]:
        """
        Получает данные для транзакции из Phosphor
        :param listing_id: id листинга
        :return: кортеж с подписью и ваучером
        """
        payload = {
            "buyer": {"eth_address": self.address},
            "listing_id": listing_id,
            "provider": "MINT_VOUCHER",
            "quantity": 1
        }
        ip, port, user, password = self.proxy.split(":")
        proxies = {
            "http": 'http://' + user + ':' + password + '@' + ip + ':' + port,
            "https": 'http://' + user + ':' + password + '@' + ip + ':' + port,
        }
        fake = Faker()
        user_agent = fake.user_agent()

        headers = {
            "Content-Type": 'application/json',
            'User-Agent': user_agent,
        }

        for _ in range(100):
            response = requests.post(
                "https://public-api.phosphor.xyz/v1/purchase-intents",
                json=payload,
                proxies=proxies,
                headers=headers
            )
            if response.status_code == 201:
                break
            logger.warning(f"Failed to send request: {response.text}")
            time.sleep(random.randint(10, 20))
        else:
            raise Exception("Can't send request")

        data = response.json()
        expiry = data['data']['voucher']['expiry']
        nonce = data['data']['voucher']['nonce']
        token_id = data['data']['voucher']['token_id']
        signature = data['data']['signature']
        voucher = ("0x0000000000000000000000000000000000000000",
                   "0x0000000000000000000000000000000000000000",
                   0,
                   1,
                   int(nonce),
                   int(expiry),
                   0,
                   int(token_id),
                   "0x0000000000000000000000000000000000000000")
        return signature, voucher


class Quest_2(Client):
    contract_address = "0xB8DD4f5Aa8AD3fEADc50F9d670644c02a07c9374"

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract: Contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0.00012, "ether")
        tx = contract.functions.safeMint(
            self.address,
            self.pop_urls_from_file(),
        ).build_transaction(self.prepare_transaction(value=value))
        return tx

    def pop_urls_from_file(self) -> str:
        """
        Читает файл data/urls.txt и возвращает первую строку, удаляя ее из файла
        :return: url из файла
        """
        with open(os.path.join("data", "urls.txt"), "r") as file:
            urls = file.read().splitlines()
            url = urls.pop(0)
        with open("data/urls.txt", "w") as file:
            file.write("\n".join(urls))
        return url


class Quest_3(Client):
    contract_address = "0x3685102bc3D0dd23A88eF8fc084a8235bE929f1c"

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0.0000029, "ether")
        tx = contract.functions.claim(
            self.address,  # _receiver (address)
            0,  # _tokenId (uint256)
            1,  # _quantity (uint256)
            "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",  # _currency (address)
            0,  # _pricePerToken (uint256)
            [  # _allowlistProof (tuple)
                ["0x0000000000000000000000000000000000000000000000000000000000000000"],  # proof (bytes32[])
                2,  # quantityLimitPerWallet (uint256)
                0,  # pricePerToken (uint256)
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"  # currency (address)
            ],
            "0x"  # _data (bytes)

        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_4(Client):
    contract_address = "0xD540038B0B427238984E0341bA49F69CD80DC139"

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_5(Client):
    contract_address = "0xf4AA97cDE2686Bc5ae2Ee934a8E5330B8B13Be64"

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_6(Client):
    contract_address = "0xc0A2a606913A49a0B0a02F682C833EFF3829B4bA"

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_7(Client):
    contract_address = "0xBcFa22a36E555c507092FF16c1af4cB74B8514C8"
    start_block = 6563000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.launchpadBuy(
            "0x0c21cfbb",
            "0x1ffca9db",
            0,
            1,
            [],
            "0x"
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_8(Client):
    contract_address = "0xF502AA456C4ACe0D77d55Ad86436F84b088486F1"
    start_block = 6608000

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mint().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_9(Client):
    contract_address = "0x32DeC694570ce8EE6AcA08598DaEeA7A3e0168A3"
    start_block = 6645000

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_16(Client):
    contract_address = "0x057b0080120d89ae21cc622db34f2d9ae9ff2bde"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mint().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_17(Client):
    contract_address = "0x0841479e87Ed8cC7374d3E49fF677f0e62f91fa1"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH().build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_19(Client):
    contract_address = "0xBcFa22a36E555c507092FF16c1af4cB74B8514C8"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.launchpadBuy(
            "0x0c21cfbb",
            "0x19a747c1",
            0,
            1,
            [],
            "0x"
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_20(Client):
    contract_address = "0xEaea2Fa0dea2D1191a584CFBB227220822E29086"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mint(
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_21(Client):
    contract_address = "0x8Ad15e54D37d7d35fCbD62c0f9dE4420e54Df403"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH(
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_22(Client):
    contract_address = "0x3A21e152aC78f3055aA6b23693FB842dEFdE0213"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintEfficientN2M_001Z5BWH(
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_23(Client):
    contract_address = "0x5A77B45B6f5309b07110fe98E25A178eEe7516c1"
    start_block = 6645000  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mint(
            self.address,
            0,
            1,
            "0x"
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_24(Client):
    contract_address = "0xBcFa22a36E555c507092FF16c1af4cB74B8514C8"
    start_block = 7025001  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """
        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.launchpadBuy(
            "0x0c21cfbb",
            "0x2968bd75",
            0,
            1,
            [],
            "0x"
        ).build_transaction(self.prepare_transaction(value=value))

        return tx


class Quest_26(Client):
    contract_address = "0xAd626D0F8BE64076C4c27a583e3df3878874467E"
    start_block = 7025001  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)
        self.proxy = self.get_proxy()


    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """

        signature, voucher = self.get_tx_data_from_phosphor("fceb2be9-f9fd-458a-8952-9a0a6f873aff")

        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintWithVoucher(
            voucher,
            signature
        ).build_transaction(self.prepare_transaction(value=value))

        return tx

class Quest_27(Client):
    contract_address = "0x3f0A935c8f3Eb7F9112b54bD3b7fd19237E441Ee"
    start_block = 7025001  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)
        self.proxy = self.get_proxy()


    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """

        signature, voucher = self.get_tx_data_from_phosphor("849e42a7-45dd-4a5b-a895-f5496e46ade2")

        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintWithVoucher(
            voucher,
            signature
        ).build_transaction(self.prepare_transaction(value=value))

        return tx

class Quest_28(Client):
    contract_address = "0x3EB78e881b28B71329344dF622Ea3A682538EC6a"
    start_block = 7025001  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)
        self.proxy = self.get_proxy()


    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """

        signature, voucher = self.get_tx_data_from_phosphor("3d595f3e-6609-405f-ba3c-d1e28381f11a")

        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintWithVoucher(
            voucher,
            signature
        ).build_transaction(self.prepare_transaction(value=value))

        return tx

class Quest_29(Client):
    contract_address = "0x3EB78e881b28B71329344dF622Ea3A682538EC6a"
    start_block = 7254696  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)
        self.proxy = self.get_proxy()


    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """

        signature, voucher = self.get_tx_data_from_phosphor("d3542d49-273c-4f2d-9d33-8904c773ed14")

        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintWithVoucher(
            voucher,
            signature
        ).build_transaction(self.prepare_transaction(value=value))

        return tx

class Quest_30(Client):
    contract_address = "0x3EB78e881b28B71329344dF622Ea3A682538EC6a"
    start_block = 7298102  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)
        self.proxy = self.get_proxy()


    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """

        signature, voucher = self.get_tx_data_from_phosphor("3c23e064-486d-46c5-8675-eabbc2e7d15e")

        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintWithVoucher(
            voucher,
            signature
        ).build_transaction(self.prepare_transaction(value=value))

        return tx

class Quest_31(Client):
    contract_address = "0x8975e0635586C6754C8D549Db0e3C7Ee807D9C8C"
    start_block = 7298102  # на случай если ранее были минты по данному контракту

    def __init__(self, pk: str) -> None:
        super().__init__(pk)
        self.proxy = self.get_proxy()


    def build_transaction(self, contract) -> dict:
        """
        Реализация абстрактного метода, строит транзакцию для конкретного минта NFT
        :param contract: инициализированный контракт
        :return: словарь с параметрами транзакции
        """

        signature, voucher = self.get_tx_data_from_phosphor("86a8741b-28dd-42ca-9f2f-dfb173a62099")

        value = self.w3.to_wei(0, "ether")
        tx = contract.functions.mintWithVoucher(
            voucher,
            signature
        ).build_transaction(self.prepare_transaction(value=value))

        return tx