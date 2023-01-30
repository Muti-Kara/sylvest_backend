from models import ChainProfile, ChainConfig


def on_app_start() -> None:
    profile, profile_created = ChainProfile.objects.get_or_create(id=1)
    config, config_created = ChainConfig.objects.get_or_create(profile=profile)

    print(f"profile created: {profile_created}, {profile}")
    print(f"config created: {config_created}, {config}")
   