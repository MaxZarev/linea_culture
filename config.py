from loguru import logger

logger.add("logs.log", level="DEBUG", rotation="10 MB", compression="zip")

# адрес rpc ноды сеть Linea, можно не менять
RPC = "https://1rpc.io/linea"

# пауза между кошельками в секундах от и до, можно не менять
pause = [100, 200]

# ОБЯЗАТЕЛЬНО апи ключ регается тут https://lineascan.build/myapikey
etherscan_api_key = ""

# перемешивать кошельки?
is_shuffle_wallets = False  # True если перемешивать

# проверять баланс?
is_check_balance = False  # True если проверять баланс
min_balance = 0.1  # минимальный баланс для проверки
