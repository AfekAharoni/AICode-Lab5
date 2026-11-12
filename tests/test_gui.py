"""Browser checks: the real server and page, driven by clicks in headless Chromium.

Setup once: pip install -r requirements-dev.txt && python -m playwright install chromium
"""

import threading
from collections.abc import Iterator

import pytest

pytest.importorskip("playwright")
from boards import board
from playwright.sync_api import Locator, Page, expect

from server import make_server
from session import Session

# White's knight takes Black's last rook, leaving king and knight against king.
CAPTURE_INTO_DRAW = board("wK e1", "bK e8", "wN d4", "bR c6")


@pytest.fixture
def session() -> Session:
    return Session()


@pytest.fixture
def url(session: Session) -> Iterator[str]:
    """Serve the given session on a free port for the length of one test."""
    server = make_server(0, session)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def open_with(
    page: Page,
    url: str,
    session: Session,
    position: tuple[dict[str, str], str] | None = None,
    opponent: str | None = None,
) -> None:
    """Optionally put a position in the session, then load the page."""
    if opponent:
        session.reset(opponent)
    if position:
        session.position = [position[0].copy(), position[1]]
    page.goto(url)
    expect(page.locator(".square")).to_have_count(64)


def square(page: Page, name: str) -> Locator:
    return page.locator(f'[data-square="{name}"]')


def play(page: Page, source: str, target: str) -> None:
    square(page, source).click()
    expect(square(page, target)).to_contain_class("target")
    square(page, target).click()


def turn(page: Page) -> Locator:
    return page.locator("#turn")


def moves(page: Page) -> Locator:
    return page.locator("#moves li span")


def test_start_page_shows_full_board(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session)
    expect(turn(page)).to_have_text("White to move")
    expect(page.locator(".square .piece")).to_have_count(32)
    expect(moves(page)).to_have_count(0)


def test_selecting_a_piece_highlights_its_moves(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session)
    square(page, "e2").click()
    expect(square(page, "e2")).to_contain_class("selected")
    expect(page.locator(".square.target")).to_have_count(2)
    expect(square(page, "e3")).to_contain_class("target")
    expect(square(page, "e4")).to_contain_class("target")


def test_playing_a_move_updates_board_and_notation(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session)
    play(page, "e2", "e4")
    expect(turn(page)).to_have_text("Black to move")
    expect(moves(page)).to_have_text(["e2-e4"])
    expect(square(page, "e4")).to_have_attribute("aria-label", "e4 White pawn")
    expect(square(page, "e2")).to_have_attribute("aria-label", "e2 empty")


def test_capturing_the_last_rook_shows_a_draw(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, (CAPTURE_INTO_DRAW, "w"))
    expect(turn(page)).to_have_text("White to move")
    play(page, "d4", "c6")
    expect(turn(page)).to_have_text("Draw by insufficient material")
    expect(moves(page)).to_have_text(["d4xc6"])
    expect(page.locator(".square .piece")).to_have_count(3)


@pytest.mark.parametrize(
    "pieces",
    [
        ("wK e1", "bK e8"),
        ("wK e1", "bK e8", "wB c1"),
        ("wK e1", "bK e8", "bN g8"),
        ("wK e1", "bK e8", "wB c1", "bB f8"),
    ],
)
def test_drawn_position_is_shown_on_load(
    page: Page, url: str, session: Session, pieces: tuple[str, ...]
) -> None:
    open_with(page, url, session, (board(*pieces), "w"))
    expect(turn(page)).to_have_text("Draw by insufficient material")


def test_pieces_cannot_be_selected_after_a_draw(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, (board("wK e1", "bK e8", "wB c1"), "w"))
    expect(turn(page)).to_have_text("Draw by insufficient material")
    for name in ("e1", "c1"):
        square(page, name).click()
        expect(page.locator(".square.selected")).to_have_count(0)
        expect(page.locator(".square.target")).to_have_count(0)


def test_enough_material_is_not_shown_as_a_draw(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, (board("wK e1", "bK e8", "wB c1", "bB c8"), "w"))
    expect(turn(page)).to_have_text("White to move")
    square(page, "c1").click()
    expect(page.locator(".square.target").first).to_be_visible()


def test_computer_replies_in_a_normal_game(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, opponent="computer")
    play(page, "e2", "e4")
    expect(moves(page)).to_have_count(2)
    expect(turn(page)).to_have_text("Your move")


def test_computer_does_not_move_after_a_draw(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, (CAPTURE_INTO_DRAW, "w"), opponent="computer")
    play(page, "d4", "c6")
    expect(turn(page)).to_have_text("Draw by insufficient material")
    page.wait_for_timeout(1200)  # longer than the computer's 500 ms pause
    expect(moves(page)).to_have_count(1)
    expect(page.locator("#message")).to_have_text("")


def test_stalemate_is_shown_as_stalemate(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, (board("bK a8", "wQ b6", "wK c1"), "b"))
    expect(turn(page)).to_have_text("Stalemate. Draw")


def test_checkmate_is_a_win_not_a_draw(page: Page, url: str, session: Session) -> None:
    mate = board("wK g1", "wR a1", "bK g8", "bP f7", "bP g7", "bP h7")
    open_with(page, url, session, (mate, "w"))
    play(page, "a1", "a8")
    expect(turn(page)).to_have_text("Checkmate. White wins")


def test_new_game_clears_a_draw(page: Page, url: str, session: Session) -> None:
    open_with(page, url, session, (board("wK e1", "bK e8"), "w"))
    expect(turn(page)).to_have_text("Draw by insufficient material")
    page.get_by_role("button", name="New game: two players").click()
    expect(turn(page)).to_have_text("White to move")
    expect(page.locator(".square .piece")).to_have_count(32)
