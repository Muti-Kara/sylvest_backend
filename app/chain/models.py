import secrets

from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _
from eth_account import Account

from api.models import ChainConfig, ChainProfile
from api.tasks import send_level_up_notification
from subjects.models import Community
from .level import ChainManager

BASE_XP_LIMIT = 1000
DIFFICULTY_PER_LEVEL = 100


class Wallet(models.Model):
    class VerifiedState(models.TextChoices):
        NONE = 'N', _('None')
        PENDING = 'P', _('Pending')
        ACCEPTED = 'A', _('Accepted')
        DENIED = 'D', _('Denied')

    wallet_address = models.CharField(
        max_length=200, unique=True, null=True, blank=True)
    verified_state = models.CharField(
        max_length=1, choices=VerifiedState.choices, default=VerifiedState.NONE
    )

    # generates a new wallet and checks if it's been generated
    def _generate_wallet_address(self) -> str:
        try:
            private_key = secrets.token_hex(32)
            addr = Account.from_key(private_key).address
            self.wallet_address = addr
            self.save()
        except Exception as e:
            print(e.with_traceback(None))
            return self._generate_wallet_address()
        return f'0x{private_key}'

    def is_verified(self) -> bool:
        return self.verified_state == self.VerifiedState.ACCEPTED


class CommunityWallet(Wallet):
    community = models.OneToOneField(Community, on_delete=models.CASCADE)


class ChainPage(Wallet):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    xp = models.PositiveBigIntegerField(default=0)
    level = models.PositiveIntegerField(default=0)
    staked_level = models.PositiveIntegerField(default=0)
    verifications = models.PositiveIntegerField(default=0)

    id_front_image = models.ImageField(null=True, blank=True, upload_to="id_images")
    id_back_image = models.ImageField(null=True, blank=True, upload_to="id_images")

    def __str__(self) -> str:
        return f'{self.user.username} chain page'

    # Stakes un-staked levels and converts them to verification rights
    def stake_levels(self) -> None:
        if self.level <= self.staked_level:
            raise Exception("Only one or more levels can be staked")
        config: ChainConfig = ChainConfig.load()
        self.verifications += (self.level - self.staked_level) \
                              * config.profile.verification_per_level
        self.staked_level = self.level
        self.save()

    def get_reward(self, action: str | None, amount: int | None = None) -> None:
        config: ChainConfig = ChainConfig.load()
        if amount is None:
            amount = config.profile.get_reward(action)
        self.xp += amount
        if self.get_current_xp() >= self.get_target_xp():
            self.level += 1
            send_level_up_notification(self.user)
        self.save()

    @staticmethod
    def level_cap(level: int) -> int:
        base: int = BASE_XP_LIMIT * (level + 1)
        diff: int = DIFFICULTY_PER_LEVEL * level
        if diff < 0:
            diff = 0
        return base + diff

    def get_current_xp(self) -> int:
        xp: int = self.xp
        curr_cap: int = self.level_cap(self.level - 1)
        return xp - curr_cap

    def get_target_xp(self) -> int:
        cap: int = self.level_cap(self.level)
        diff: int = self.level * BASE_XP_LIMIT
        return cap - diff

    def save(self, *args, **kwargs):
        if self.verified_state == self.VerifiedState.ACCEPTED \
                and not self.wallet_address:
            self._generate_wallet_address()
        super(ChainPage, self).save(*args, **kwargs)


class TransferRequest(models.Model):
    amount = models.PositiveIntegerField()
    from_addr = models.CharField(max_length=200)
    to_addr = models.CharField(max_length=200)
    verified_by = models.ManyToManyField(User)

    def verify(self, user: User):
        if self.verified_by.all().contains(user):
            raise Exception("Same user can't verify same transaction twice")
        chain_page: ChainPage = user.chainpage
        chain_page.verifications = user.chainpage.verifications - 1
        config: ChainConfig = ChainConfig.load()
        ChainManager().send(
            "mint",
            user.chainpage.wallet_address,
            config.profile.token_per_verification
        )

        self.verified_by.add(user)
        chain_page.save()
        self.save()

    def __str__(self) -> str:
        return f"Transaction from {self.from_addr}"
