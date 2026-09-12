import pytest
from pydantic import ValidationError

from rupturelab.config import Settings


def test_settings_accept_supported_environment_and_positive_timeouts() -> None:
    settings = Settings(
        environment="production",
        proxy_timeout_seconds=2.5,
        experiment_timeout_seconds=30,
    )

    assert settings.environment == "production"
    assert settings.proxy_timeout_seconds == 2.5
    assert settings.experiment_timeout_seconds == 30


def test_settings_reject_invalid_environment_and_timeouts() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"environment": "staging"})

    with pytest.raises(ValidationError):
        Settings(proxy_timeout_seconds=0)

    with pytest.raises(ValidationError):
        Settings(experiment_timeout_seconds=301)
