import os
import logging
import multiprocessing
from datetime import datetime

env = os.getenv('ENV')
if env not in ('cardona', 'mainnet', 'bali'):
    raise ValueError("ENV must be 'cardona' or 'mainnet'")

if env == 'cardona':
    EP = "https://rpc.cardona.zkevm-rpc.com"
    EP_DEBUG = "<YOUR DEBUG ENDPOINT FOR CARDONA HERE>"
    OUTPUT_FOLDER = "zkevm_cardona"
    TRANSACTIONS_FOLDER = "zkevm_cardona/transactions"
elif env == 'mainnet':
    EP = "https://zkevm-rpc.com"
    EP_DEBUG = "<YOUR DEBUG ENDPOINT FOR MAINNET HERE>"
    OUTPUT_FOLDER = "zkevm_mainnet"
    TRANSACTIONS_FOLDER = "zkevm_mainnet/transactions"
elif env == 'bali':
    EP = "https://rpc.internal.zkevm-rpc.com"
    EP_DEBUG = "<YOUR DEBUG ENDPOINT FOR BALI HERE>"
    OUTPUT_FOLDER = "zkevm_bali"
    TRANSACTIONS_FOLDER = "zkevm_bali/transactions"

CONTRACTS_FILE = "contracts.json"
OPCODES_FILE = "opcodes.json"
CONFLICTS_FILE = "conflicts.json"
REVERTED_FILE = "reverted.json"
CHANGED_FILE = "changed.json"
NO_CONTRACTS_CACHE = "no_contracts.json"
TRACE_CACHE_FILE = "trace_cache.json"

DOWNLOAD_BATCHES_PER_ITER = 10000
DOWNLOAD_QUERIES_PER_REQUEST = 20
TRACES_QUERIES_PER_REQUEST = 5  # Traces can be very large

# OPCODES
UNSUPPORTED_OPCODES = ("49", "4a", "5c", "5d", "5e")
UNSUPPORTED_OPCODES_NAMES = \
    ('BLOBHASH', 'BLOBBASEFEE', 'TLOAD', 'TSTORE', 'MCOPY')

CHANGED_OPCODES = ("ff", "3f", "40", "44")
CHANGED_OPCODES_NAMES = \
    ('SELFDESTRUCT', 'EXTCODEHASH', 'BLOCKHASH', 'DIFFICULTY')

# CPU / MULTITHREAD PROCESSING
THREAD_COUNT = multiprocessing.cpu_count()

# FUNCS & INITIALIZATION
LOGLEVEL = os.environ.get('LOGLEVEL', logging.INFO)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ca')
logger.setLevel(LOGLEVEL)


def msg(x):
    now = datetime.now()
    return \
        f"[{now.year}-{now.month:02}-{now.day:02} " \
        f"{now.hour:02}:{now.minute:02}:{now.second:02}] {x}"


def linfo(x): logger.info(msg(x))
def ldebug(x): logger.debug(msg(x))
def lerror(x): logger.error(msg(x))
