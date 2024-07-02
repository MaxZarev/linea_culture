import json
import random

import requests
from hexbytes import HexBytes
from web3 import Web3

from config import *


class Client:
    def __init__(self, pk: str):
        self.w3 = Web3(Web3.HTTPProvider(RPC))
        self.pk = pk
        self.address = self.w3.eth.account.from_key(pk).address

    @staticmethod
    def get_list_from_file(path: str) -> list[str]:
        """
        Читает файл и возвращает список строк
        :param path: название файла
        :return:
        """
        with open(path, "r") as file:
            return file.read().splitlines()

    def pop_urls_from_file(self) -> str:
        """
        Берет из файла urls.txt первую строку и удаляет ее
        :return: строчка с url
        """
        with open("data/urls.txt", "r") as file:
            urls = file.read().splitlines()
            url = urls.pop(0)
        with open("data/urls.txt", "w") as file:
            file.write("\n".join(urls))
        return url


    def mint_nft(self) -> bool:
        balance = self.w3.eth.get_balance(self.address)
        if is_check_balance:
            if balance < min_balance / 3500 * 10 ** 18:  # проверка баланса
                logger.error(f"{self.address} : Not enough balance!")
                return False

        contract_address = self.w3.to_checksum_address("0xB8DD4f5Aa8AD3fEADc50F9d670644c02a07c9374")
        abi = self.get_abi()
        contract = self.w3.eth.contract(address=contract_address, abi=abi)

        tx = contract.functions.safeMint(
            self.address,
            self.pop_urls_from_file(),
        ).build_transaction(self.prepare_transaction(value=int(0.00012 * 10 ** 18)))

        tx_hash = self.send_transaction(tx)
        logger.info(f"{self.address} minted: {tx_hash.hex()}")
        return True

    def send_transaction(self, transaction: dict, gas: int = 0) -> HexBytes:
        if gas:
            transaction['gas'] = gas
        else:
            transaction['gas'] = int((self.w3.eth.estimate_gas(transaction)) * random.uniform(*gas_coef))

        signed_tx = self.w3.eth.account.sign_transaction(transaction, self.pk)

        return self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    def get_abi(self) -> str:
        with open("data/abi.json") as f:
            return json.loads(f.read())

    def prepare_transaction(self, value: int = 0) -> dict:
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

    def get_priority_fee(self):
        fee_history = self.w3.eth.fee_history(25, 'latest', [20.0])
        non_empty_block_priority_fees = [fee[0] for fee in fee_history["reward"] if fee[0] != 0]

        divisor_priority = max(len(non_empty_block_priority_fees), 1)

        priority_fee = int(round(sum(non_empty_block_priority_fees) / divisor_priority))

        return priority_fee

    def is_minted(self):
        url = (f"https://api.lineascan.build/api"
               f"?module=account"
               f"&action=txlist"
               f"&address={self.address}"
               f"&startblock=0"
               f"&endblock=99999999"
               f"&page=1"
               f"&offset=100"
               f"&sort=asc"
               f"&apikey={lineascan_api_key}")
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"Can't get data from etherscan: {response.text}")
        if response.json()['status'] == "1":
            json_response = response.json()
            for tx in json_response['result']:
                if tx['to'].lower() == "0xB8DD4f5Aa8AD3fEADc50F9d670644c02a07c9374".lower() and tx['txreceipt_status'] == "1":
                    return True
        return False

    def write_result(self):
        with open("data/result.txt", "a") as file:
            file.write(self.address + "\n")

