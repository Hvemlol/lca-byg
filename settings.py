import os

import keyring
import keyring.errors

SERVICE_NAME = "lca-byg"
KEY_NAME = "openai_api_key"


def _safe_keyring_call(func, *args, **kwargs):
    """keyring raises NoKeyringError on headless systems without a secret
    service (e.g. Linux without D-Bus/Secret Service). Degrade gracefully."""
    try:
        return func(*args, **kwargs)
    except (keyring.errors.NoKeyringError, keyring.errors.KeyringError):
        return None


def get_api_key() -> str | None:
    stored = _safe_keyring_call(keyring.get_password, SERVICE_NAME, KEY_NAME)
    return stored or os.environ.get("OPENAI_API_KEY")


def set_api_key(api_key: str) -> None:
    keyring.set_password(SERVICE_NAME, KEY_NAME, api_key.strip())


def clear_api_key() -> None:
    try:
        keyring.delete_password(SERVICE_NAME, KEY_NAME)
    except keyring.errors.PasswordDeleteError:
        pass
