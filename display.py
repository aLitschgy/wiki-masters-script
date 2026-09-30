"""Colored display of the cards obtained."""
import os
import sys

RESET = "\033[0m"
# Rarity code -> ANSI color (unknown rarities are shown in white).
RARITY_COLORS = {
    "C": "\033[92m",         # light green
    "PC": "\033[96m",        # light blue
    "R": "\033[35m",         # purple
    "SR": "\033[95m",        # magenta
    "UR": "\033[38;5;208m",  # orange
    "L": "\033[93m",         # gold
}
DEFAULT_COLOR = "\033[97m"
# Colors on an interactive terminal, or forced with FORCE_COLOR=1 (e.g. docker logs).
USE_COLOR = "NO_COLOR" not in os.environ and (sys.stdout.isatty() or os.environ.get("FORCE_COLOR") == "1")


def paint(text: str, color: str) -> str:
    return f"{color}{text}{RESET}" if USE_COLOR else text


def print_pack(index: int, data: dict) -> None:
    shiny_ids = {c["card_id"] for c in data.get("owned_copies", []) if c.get("is_shiny")}
    print(f"[{index}] (remaining: {data.get('packs_remaining', '?')})")
    for card in data.get("cards", []):
        rarity = card.get("rarity", "?")
        color = RARITY_COLORS.get(rarity, DEFAULT_COLOR)
        shiny = " ✨" if card["id"] in shiny_ids else ""
        print("   " + paint(f"[{rarity}] {card['wikipedia_title']}{shiny}", color))
