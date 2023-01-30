from web3.contract import Contract
from hexbytes import HexBytes
from django_redis import get_redis_connection
from redis import Redis
from decimal import Decimal
from web3 import Web3
import configuration
from ast import literal_eval
import time

from chain.exceptions import ZeroAmount, TransacitonFailed, InvalidInput, ImpossibleTransaction

CHAIN_ABI = configuration.CHAIN_ABI
CHAIN_URL = configuration.CHAIN_URL
CHAIN_ID = int(configuration.CHAIN_ID)
MASTER_ADDRESS = configuration.MASTER_ADDRESS
MASTER_KEY = configuration.MASTER_KEY
CHAIN_ADDRESS = configuration.TOKEN_ADDRESS


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ChainAttributes:
    connected: bool | None = False
    balance: Decimal | None = None
    address: str | None = None

    def __init__(self, connected: bool, address: str, balance: Decimal | None = None) -> None:
        self.connected = connected
        self.balance = balance
        self.address = address

    def __dict__(self):
        return {
            'connected': self.connected,
            'balance': f"{self.balance:.6f}" if self.balance is not None else None,
        }


class ChainManager(metaclass=Singleton):
    class Functions:
        ON_TRANSACTION_VERIFIED = "verifiedTransfer"
        SEND_TOKEN = "sendToken"
        MINT = "mint"
        BURN = "burn"
        NEW_WALLET = "newWallet"
        BALANCE_OF = "balanceOf"

    w3 = Web3(Web3.HTTPProvider(CHAIN_URL))
    contract: Contract = w3.eth.contract(address=CHAIN_ADDRESS, abi=CHAIN_ABI)
    filter = contract.events.TransferRequest.createFilter(fromBlock="latest")
    latest_event_hash = None
    nonce = w3.eth.get_transaction_count(MASTER_ADDRESS)

    def chain_attributes(self, address: str | None) -> ChainAttributes:
        attributes: ChainAttributes = ChainAttributes(
            connected=self.w3.isConnected(),
            address=address
        )
        if not address:
            return attributes
        if attributes.connected:
            attributes.balance = Decimal(self.call("balanceOf", address))
        return attributes

    def exp_decimals(self) -> int:
        return pow(10, self.call("decimals"))

    def get_transfer_logs(self):
        try:
            logs = self.filter.get_new_entries()
        except Exception as e:
            if e.args[0]["message"] == "filter not found":
                self.filter = self.contract\
                    .events.TransferRequest.createFilter(fromBlock="latest")
            temp = self.contract\
                .events.TransferRequest.createFilter(fromBlock=0, toBlock="latest")
            all_logs = temp.get_all_entries()
            index: int
            for idx in range(len(all_logs)):
                if self.latest_event_hash == all_logs[idx]["transactionHash"]:
                    index = idx
                    break
            logs = all_logs[(index + 1):]
        self.latest_event_hash = logs[-1]["transactionHash"] if len(logs) > 0 else None
        return [transfer_requests["args"] for transfer_requests in logs]

    def update_nonce(self, recalibrate: bool = False):
        if recalibrate:
            self.nonce = self.w3.eth.get_transaction_count(MASTER_ADDRESS)
        else:
            self.nonce += 1

    def get_nonce(self) -> int:
        return self.nonce

    def send(self, func_name: str, *args):
        from chain.tasks import generate_transaction
        generate_transaction(func_name, *args)

    def call(self, func_name: str, *args):
        return self.contract.functions[func_name](*args).call()


class Transaction:
    txn: dict
    address: str
    error: int = 0
    chain = ChainManager()

    def __init__(self, func_name: str, *args):
        if func_name == "cached":
            self.address = args[0]["address"]
            self.txn = args[0]["txn"]
            return

        from_addr = None
        to_addr = None
        amount = None
        match len(args):
            case 3:
                from_addr = args[0]
                to_addr = args[1]
                amount = args[2]
            case 2:
                to_addr = args[0]
                amount = args[1]
            case 1:
                to_addr = args[0]

        if to_addr is None:
            raise InvalidInput()

        if (amount is not None) and amount == 0:
            raise ZeroAmount()

        if (from_addr is not None) and self.chain.call("balanceOf", from_addr) < amount:
            raise ImpossibleTransaction()

        self.txn = self.chain.contract.functions[func_name](*args).buildTransaction({
            "chainId": CHAIN_ID,
            "gasPrice": self.chain.w3.eth.gasPrice,
            "from": MASTER_ADDRESS,
            "nonce": 0
        })

        self.address = to_addr

    def sign(self) -> HexBytes:
        if self.error == 10:
            raise TransacitonFailed()
        self.txn["nonce"] = self.chain.get_nonce()
        self.chain.update_nonce()
        signed_tx = self.chain.w3.eth.account.sign_transaction(self.txn, private_key=MASTER_KEY)
        try:
            return self.chain.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        except Exception as e:
            self.error += 1
            if type(e) == ValueError:
                match e.args[0]["message"]:
                    case "nonce too low":
                        self.chain.update_nonce(recalibrate=True)
                        self.txn["nonce"] = self.chain.get_nonce()
                        return self.sign()
                    case "transaction underpriced" | "replacement transaction underpriced":
                        self.txn["gasPrice"] = int(1.1 * self.txn["gasPrice"])
                        return self.sign()
                    case _:
                        raise e

    def safe_sign(self):
        if self.error == 10:
            raise TransacitonFailed()
        bef_t_balance = self.chain.call("balanceOf", self.address)
        try:
            tx_receipt = self.chain.w3.eth.wait_for_transaction_receipt(self.sign(), poll_latency=0.75)
        except Exception as e:
            if type(e) == ValueError and int(e.args[0]["code"]) == 429:
                time.sleep(20)
                self.safe_sign()
            else:
                return
        aft_t_balance = self.chain.call("balanceOf", self.address)
        if aft_t_balance - bef_t_balance == 0 or tx_receipt["status"] == 0:
            self.error += 1
            self.safe_sign()

    def __str__(self) -> str:
        return str({"txn": self.txn, "address": self.address})

    @staticmethod
    def from_bytes(txn: bytes) -> "Transaction":
        txn_dict = literal_eval(txn.decode("utf-8"))
        return Transaction("cached", txn_dict)


class SignManager(metaclass=Singleton):
    cache: Redis = get_redis_connection()

    def add_txn(self, txn: Transaction):
        self.cache.rpush("txn_queue:", str(txn))

    def has_next(self) -> bool:
        if not self.cache.exists("txn_queue:"):
            self.cache.set("signing", "0")
        return self.is_signing()

    def start_signing(self):
        self.cache.set("signing", "1")
        while self.has_next():
            txn: Transaction = Transaction.from_bytes(self.cache.lpop("txn_queue:"))
            txn.safe_sign()

    def is_signing(self) -> bool:
        return int(self.cache.get("signing")) == 1
