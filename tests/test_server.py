"""The HTTP layer: routes, request validation, and command-line arguments."""

import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from http.server import HTTPServer
from pathlib import Path
from typing import Any

import pytest

from server import build_server, make_server
from session import Session


def serve(server: HTTPServer) -> str:
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_port}"


@pytest.fixture
def url() -> Iterator[str]:
    server = make_server(0, Session())
    yield serve(server)
    server.shutdown()
    server.server_close()


def send(url: str, path: str, body: bytes | None = None) -> tuple[int, Any]:
    request = urllib.request.Request(
        url + path, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_unknown_paths_are_not_found(url: str) -> None:
    assert send(url, "/nowhere") == (404, {"error": "Not found"})
    assert send(url, "/nowhere", b"{}") == (404, {"error": "Not found"})


@pytest.mark.parametrize(
    ("body", "error"),
    [
        (b"[1, 2]", "Expected an action object"),
        (b'{"action": "fly"}', "Unknown action"),
        (b'{"action": "move", "source": "e2"}', "Expected a source and a target square"),
        (b'{"action": "move", "source": "e2", "target": "e5"}', "That move is not allowed"),
        (b"not json", "Expecting value"),
    ],
)
def test_bad_actions_are_rejected_without_changing_the_game(
    url: str, body: bytes, error: str
) -> None:
    status, reply = send(url, "/api/action", body)
    assert status == 400
    assert error in reply["error"]
    assert send(url, "/api/state")[1]["moves"] == []


def test_oversized_request_is_rejected(url: str) -> None:
    request = urllib.request.Request(
        url + "/api/action", data=b"{}", headers={"Content-Length": "2000000"}
    )
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(request)
    assert caught.value.code == 400
    assert json.load(caught.value) == {"error": "Invalid request size"}


def test_save_file_argument_is_used_for_save_and_load(tmp_path: Path) -> None:
    """Regression: --save-file was passed where make_server expects a Session."""
    path = tmp_path / "chosen.save.json"
    server = build_server(["--port", "0", "--save-file", str(path)])
    try:
        url = serve(server)
        send(url, "/api/action", b'{"action": "move", "source": "e2", "target": "e4"}')
        assert send(url, "/api/action", b'{"action": "save"}')[0] == 200
        assert json.loads(path.read_text())["moves"] == [["e2", "e4"]]
    finally:
        server.shutdown()
        server.server_close()
