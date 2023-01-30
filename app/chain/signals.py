from django.db.models.signals import post_save
from django.dispatch import receiver

from api.models import ChainConfig
from chain.level import ChainManager
from .models import TransferRequest


@receiver(post_save, sender=TransferRequest)
def on_save(sender, instance: TransferRequest, created, **kwargs):
    config: ChainConfig = ChainConfig.load()
    if instance.verified_by.count() >= config.profile.target_approval_number:
        ChainManager().send(
            ChainManager.Functions.ON_TRANSACTION_VERIFIED,
            instance.from_addr,
            instance.to_addr,
            instance.amount
        )
        instance.delete()
