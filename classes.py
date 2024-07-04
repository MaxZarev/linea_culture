import json
import os
import random
from abc import abstractmethod

import requests
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.types import Wei

from config import *


class Client:
    contract_address = ""

    def __init__(self, pk: str):
        self.w3 = Web3(Web3.HTTPProvider(RPC))
        self.pk = pk
        self.address = self.w3.eth.account.from_key(pk).address
        self.abi = self.__class__.__name__.lower()

    @staticmethod
    def get_list_from_file(path: str) -> list[str]:
        """
        Читает файл и возвращает список строк
        :param path: название файла
        :return:
        """
        with open(path, "r") as file:
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
        if is_check_balance:
            balance = self.w3.eth.get_balance(self.address)
            if balance < min_balance / 3500 * 10 ** 18:
                logger.error(f"{self.address} : Not enough balance!")
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
               f"&startblock=6084611"
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
                logger.warning(f"{self.address} : вероятно на данном кошельке не делали квесты в Linea Culture")
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

    @abstractmethod
    def build_transaction(self, contract):
        pass

    def mint_nft(self) -> bool:
        # проверяем баланс, если нужно
        if self.check_balance():
            return False

        contract = self.get_contract()

        tx = self.build_transaction(contract)

        tx_hash = self.send_transaction(tx)
        logger.info(f"{self.address} minted: {tx_hash.hex()}")
        return True


class Quest_2(Client):
    contract_address = "0xB8DD4f5Aa8AD3fEADc50F9d670644c02a07c9374"

    def __init__(self, pk: str):
        super().__init__(pk)

    def build_transaction(self, contract) -> dict:
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
            self.address,                                                               # _receiver (address)
            0,                                                                          # _tokenId (uint256)
            1,                                                                          # _quantity (uint256)
            "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",                               # _currency (address)
            0,                                                                          # _pricePerToken (uint256)
            [                                                                           # _allowlistProof (tuple)
                ["0x0000000000000000000000000000000000000000000000000000000000000000"],   # proof (bytes32[])
                2,                                                                      # quantityLimitPerWallet (uint256)
                0,                                                                      # pricePerToken (uint256)
                "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"                            # currency (address)
            ],
            "0x"                                                                        # _data (bytes)

        ).build_transaction(self.prepare_transaction(value=value))

        return tx

