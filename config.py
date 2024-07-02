from loguru import logger

logger.add("data/logs.log", level="DEBUG", rotation="10 MB", compression="zip")

# адрес rpc ноды сеть Linea, можно не менять
RPC = "https://1rpc.io/linea"

# пауза между кошельками в секундах от и до, можно не менять
pause = [100, 200]

# ОБЯЗАТЕЛЬНО апи ключ регается тут https://lineascan.build/myapikey
lineascan_api_key = ""

# перемешивать кошельки?
is_shuffle_wallets = False  # True если перемешивать

# проверять баланс?
is_check_balance = False  # True если проверять баланс
min_balance = 0.1  # минимальный баланс для проверки

# коэффициент надбавки рандомного газа, указывай 2 числа от 1 до 2
gas_coef = [1.1, 1.3]


