from celery import shared_task

from chain.models import TransferRequest
from chain.level import ChainManager, SignManager, Transaction


@shared_task(name="create_transfer_log")
def create_transfer_log():
    log_data = ChainManager().get_transfer_logs()
    for log in log_data:
        TransferRequest.objects.create(
            from_addr=log["from"],
            to_addr=log["to"],
            amount=log["amount"]
        )
    print(f"{len(log_data)} logs created.")


@shared_task(name="sign_transactions")
def sign_transactions():
    if SignManager().is_signing():
        print("Signing already")
        return
    SignManager().start_signing()

@shared_task
def generate_transaction(func_name: str, *args):
    SignManager().add_txn(Transaction(func_name, *args))
