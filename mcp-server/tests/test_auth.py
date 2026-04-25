import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock, patch, mock_open

ENV_CONTENT = "TENANT_ID=test-tenant\nCLIENT_ID=test-client\n"

def test_get_token_uses_cache_when_available(tmp_path, mocker):
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{}")
    env_path = tmp_path / "test.env"
    env_path.write_text(ENV_CONTENT)

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = [{"username": "test@test.com"}]
    mock_app.acquire_token_silent.return_value = {"access_token": "cached-token"}

    mocker.patch("auth.ENV_PATH", env_path)
    mocker.patch("auth.CACHE_PATH", cache_path)
    mocker.patch("msal.PublicClientApplication", return_value=mock_app)

    from auth import get_token
    token = get_token()

    assert token == "cached-token"
    mock_app.acquire_token_silent.assert_called_once()
    mock_app.initiate_device_flow.assert_not_called()

def test_get_token_raises_reauth_instruction_when_no_cache(tmp_path, mocker):
    env_path = tmp_path / "test.env"
    env_path.write_text(ENV_CONTENT)

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = []
    mock_app.initiate_device_flow.return_value = {"message": "Go to https://microsoft.com/devicelogin"}
    mock_app.acquire_token_by_device_flow.return_value = {"access_token": "new-token"}

    mocker.patch("auth.ENV_PATH", env_path)
    mocker.patch("auth.CACHE_PATH", tmp_path / "nonexistent.json")
    mocker.patch("msal.PublicClientApplication", return_value=mock_app)

    from auth import get_token
    with pytest.raises(RuntimeError, match="refresh_auth.py"):
        get_token()

    mock_app.initiate_device_flow.assert_called_once()
    mock_app.acquire_token_by_device_flow.assert_not_called()

def test_get_token_raises_reauth_instruction_before_inline_auth_failure(tmp_path, mocker):
    env_path = tmp_path / "test.env"
    env_path.write_text(ENV_CONTENT)

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = []
    mock_app.initiate_device_flow.return_value = {"message": "Go to ..."}
    mock_app.acquire_token_by_device_flow.return_value = {
        "error": "authorization_declined",
        "error_description": "User declined"
    }

    mocker.patch("auth.ENV_PATH", env_path)
    mocker.patch("auth.CACHE_PATH", tmp_path / "nonexistent.json")
    mocker.patch("msal.PublicClientApplication", return_value=mock_app)

    from auth import get_token
    with pytest.raises(RuntimeError, match="refresh_auth.py"):
        get_token()
    mock_app.acquire_token_by_device_flow.assert_not_called()

def test_get_token_requests_correct_scope_for_bap(tmp_path, mocker):
    env_path = tmp_path / "test.env"
    env_path.write_text(ENV_CONTENT)

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = [{"username": "test@test.com"}]
    mock_app.acquire_token_silent.return_value = {"access_token": "bap-token"}

    mocker.patch("auth.ENV_PATH", env_path)
    mocker.patch("auth.CACHE_PATH", tmp_path / "cache.json")
    mocker.patch("msal.PublicClientApplication", return_value=mock_app)

    from auth import get_token
    get_token("https://api.bap.microsoft.com")

    mock_app.acquire_token_silent.assert_called_with(
        ["https://api.bap.microsoft.com/.default"],
        account=mock_app.get_accounts.return_value[0]
    )
