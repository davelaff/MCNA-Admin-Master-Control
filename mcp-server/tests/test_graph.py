import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from graph import graph_get, graph_get_all, graph_post, GraphError

TOKEN = "fake-token"

def _mock_response(status=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.text = ""
    resp.content = b"content"
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status}")
    return resp

def test_graph_get_success():
    with patch("requests.get", return_value=_mock_response(200, {"id": "abc"})) as mock_get:
        result = graph_get("/users/abc", TOKEN)
    assert result == {"id": "abc"}
    mock_get.assert_called_once()

def test_graph_get_raises_on_401():
    with patch("requests.get", return_value=_mock_response(401)):
        with pytest.raises(GraphError) as exc:
            graph_get("/users/abc", TOKEN)
    assert exc.value.status == 401

def test_graph_get_raises_on_403():
    with patch("requests.get", return_value=_mock_response(403)):
        with pytest.raises(GraphError) as exc:
            graph_get("/users/abc", TOKEN)
    assert exc.value.status == 403

def test_graph_get_retries_on_429_and_succeeds():
    responses = [
        _mock_response(429, headers={"Retry-After": "1"}),
        _mock_response(200, {"value": []}),
    ]
    with patch("requests.get", side_effect=responses), patch("time.sleep"):
        result = graph_get("/users", TOKEN)
    assert result == {"value": []}

def test_graph_get_raises_on_double_429():
    responses = [
        _mock_response(429, headers={"Retry-After": "1"}),
        _mock_response(429, headers={"Retry-After": "1"}),
    ]
    with patch("requests.get", side_effect=responses), patch("time.sleep"):
        with pytest.raises(GraphError) as exc:
            graph_get("/users", TOKEN)
    assert exc.value.status == 429

def test_graph_get_all_follows_next_link():
    page1 = {"value": [{"id": "1"}], "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=abc"}
    page2 = {"value": [{"id": "2"}]}
    responses = [_mock_response(200, page1), _mock_response(200, page2)]
    with patch("requests.get", side_effect=responses):
        result = graph_get_all("/users", TOKEN)
    assert result == [{"id": "1"}, {"id": "2"}]

def test_graph_post_success():
    with patch("requests.post", return_value=_mock_response(200, {"id": "new"})):
        result = graph_post("/me/sendMail", TOKEN, {"message": {}})
    assert result == {"id": "new"}
