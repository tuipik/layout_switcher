from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from evdev import ecodes


def _kc(name: str) -> int:
    return ecodes.ecodes[name]


def _build_bidirectional_map(pairs: Iterable[Tuple[str, str]]) -> Tuple[Dict[str, str], Dict[str, str]]:
    forward: Dict[str, str] = {}
    reverse: Dict[str, str] = {}
    for left, right in pairs:
        forward[left] = right
        reverse[right] = left
    return forward, reverse


# English (US) <-> Ukrainian (Standard) mapping by physical key position.
# This does not rely on the system layout and is used for translation.
_EN_UK_PAIRS = [
    ("q", "й"), ("w", "ц"), ("e", "у"), ("r", "к"), ("t", "е"), ("y", "н"), ("u", "г"),
    ("i", "ш"), ("o", "щ"), ("p", "з"), ("[", "х"), ("]", "ї"), ("\\", "ґ"),
    ("a", "ф"), ("s", "і"), ("d", "в"), ("f", "а"), ("g", "п"), ("h", "р"), ("j", "о"),
    ("k", "л"), ("l", "д"), (";", "ж"), ("'", "є"),
    ("z", "я"), ("x", "ч"), ("c", "с"), ("v", "м"), ("b", "и"), ("n", "т"), ("m", "ь"),
    (",", "б"), (".", "ю"), ("/", "."),
    ("Q", "Й"), ("W", "Ц"), ("E", "У"), ("R", "К"), ("T", "Е"), ("Y", "Н"), ("U", "Г"),
    ("I", "Ш"), ("O", "Щ"), ("P", "З"), ("{", "Х"), ("}", "Ї"), ("|", "Ґ"),
    ("A", "Ф"), ("S", "І"), ("D", "В"), ("F", "А"), ("G", "П"), ("H", "Р"), ("J", "О"),
    ("K", "Л"), ("L", "Д"), (":", "Ж"), ("\"", "Є"),
    ("Z", "Я"), ("X", "Ч"), ("C", "С"), ("V", "М"), ("B", "И"), ("N", "Т"), ("M", "Ь"),
    ("<", "Б"), (">", "Ю"), ("?", ","),
    ("1", "1"), ("!", "!"),
    ("2", "2"), ("@", "\""),
    ("3", "3"), ("#", "№"),
    ("4", "4"), ("$", ";"),
    ("5", "5"), ("%", "%"),
    ("6", "6"), ("^", ":"),
    ("7", "7"), ("&", "?"),
    ("8", "8"), ("*", "*"),
    ("9", "9"), ("(", "("),
    ("0", "0"), (")", ")"),
    ("-", "-"), ("_", "_"),
    ("=", "="), ("+", "+"),
    ("`", "'"), ("~", "\""),
]

EN_TO_UK, UK_TO_EN = _build_bidirectional_map(_EN_UK_PAIRS)


@dataclass(frozen=True)
class TranslationDirection:
    source: str
    target: str


class Translator:
    def __init__(self, primary: str, secondary: str) -> None:
        self.primary = primary
        self.secondary = secondary

    def translate(self, text: str, source: str, target: str) -> str:
        mapping = self._get_map(source, target)
        return "".join(mapping.get(char, char) for char in text)

    def detect_direction(self, text: str, fallback_source: str) -> TranslationDirection:
        primary_to_secondary = EN_TO_UK if self.primary == "en" else UK_TO_EN
        secondary_to_primary = UK_TO_EN if self.primary == "en" else EN_TO_UK

        count_primary = sum(1 for ch in text if ch in primary_to_secondary)
        count_secondary = sum(1 for ch in text if ch in secondary_to_primary)

        if count_secondary > count_primary:
            return TranslationDirection(source=self.secondary, target=self.primary)
        if count_primary > count_secondary:
            return TranslationDirection(source=self.primary, target=self.secondary)
        if fallback_source == self.primary:
            return TranslationDirection(source=self.primary, target=self.secondary)
        return TranslationDirection(source=self.secondary, target=self.primary)

    def _get_map(self, source: str, target: str) -> Dict[str, str]:
        if {source, target} != {"en", "uk"}:
            raise ValueError(f"Unsupported language pair: {source} -> {target}")
        if source == "en" and target == "uk":
            return EN_TO_UK
        return UK_TO_EN


class KeyMapper:
    def __init__(self) -> None:
        self._layouts = {
            "en": {
                "letters": {
                    _kc("KEY_Q"): "q", _kc("KEY_W"): "w", _kc("KEY_E"): "e", _kc("KEY_R"): "r",
                    _kc("KEY_T"): "t", _kc("KEY_Y"): "y", _kc("KEY_U"): "u", _kc("KEY_I"): "i",
                    _kc("KEY_O"): "o", _kc("KEY_P"): "p", _kc("KEY_A"): "a", _kc("KEY_S"): "s",
                    _kc("KEY_D"): "d", _kc("KEY_F"): "f", _kc("KEY_G"): "g", _kc("KEY_H"): "h",
                    _kc("KEY_J"): "j", _kc("KEY_K"): "k", _kc("KEY_L"): "l", _kc("KEY_Z"): "z",
                    _kc("KEY_X"): "x", _kc("KEY_C"): "c", _kc("KEY_V"): "v", _kc("KEY_B"): "b",
                    _kc("KEY_N"): "n", _kc("KEY_M"): "m",
                },
                "non_letters": {
                    _kc("KEY_1"): ("1", "!"),
                    _kc("KEY_2"): ("2", "@"),
                    _kc("KEY_3"): ("3", "#"),
                    _kc("KEY_4"): ("4", "$"),
                    _kc("KEY_5"): ("5", "%"),
                    _kc("KEY_6"): ("6", "^"),
                    _kc("KEY_7"): ("7", "&"),
                    _kc("KEY_8"): ("8", "*"),
                    _kc("KEY_9"): ("9", "("),
                    _kc("KEY_0"): ("0", ")"),
                    _kc("KEY_MINUS"): ("-", "_"),
                    _kc("KEY_EQUAL"): ("=", "+"),
                    _kc("KEY_LEFTBRACE"): ("[", "{"),
                    _kc("KEY_RIGHTBRACE"): ("]", "}"),
                    _kc("KEY_BACKSLASH"): ("\\", "|"),
                    _kc("KEY_SEMICOLON"): (";", ":"),
                    _kc("KEY_APOSTROPHE"): ("'", "\""),
                    _kc("KEY_GRAVE"): ("`", "~"),
                    _kc("KEY_COMMA"): (",", "<"),
                    _kc("KEY_DOT"): (".", ">"),
                    _kc("KEY_SLASH"): ("/", "?"),
                },
            },
            "uk": {
                "letters": {
                    _kc("KEY_Q"): "й", _kc("KEY_W"): "ц", _kc("KEY_E"): "у", _kc("KEY_R"): "к",
                    _kc("KEY_T"): "е", _kc("KEY_Y"): "н", _kc("KEY_U"): "г", _kc("KEY_I"): "ш",
                    _kc("KEY_O"): "щ", _kc("KEY_P"): "з", _kc("KEY_LEFTBRACE"): "х",
                    _kc("KEY_RIGHTBRACE"): "ї", _kc("KEY_BACKSLASH"): "ґ", _kc("KEY_A"): "ф",
                    _kc("KEY_S"): "і", _kc("KEY_D"): "в", _kc("KEY_F"): "а", _kc("KEY_G"): "п",
                    _kc("KEY_H"): "р", _kc("KEY_J"): "о", _kc("KEY_K"): "л", _kc("KEY_L"): "д",
                    _kc("KEY_SEMICOLON"): "ж", _kc("KEY_APOSTROPHE"): "є", _kc("KEY_Z"): "я",
                    _kc("KEY_X"): "ч", _kc("KEY_C"): "с", _kc("KEY_V"): "м", _kc("KEY_B"): "и",
                    _kc("KEY_N"): "т", _kc("KEY_M"): "ь", _kc("KEY_COMMA"): "б",
                    _kc("KEY_DOT"): "ю",
                },
                "non_letters": {
                    _kc("KEY_1"): ("1", "!"),
                    _kc("KEY_2"): ("2", "\""),
                    _kc("KEY_3"): ("3", "№"),
                    _kc("KEY_4"): ("4", ";"),
                    _kc("KEY_5"): ("5", "%"),
                    _kc("KEY_6"): ("6", ":"),
                    _kc("KEY_7"): ("7", "?"),
                    _kc("KEY_8"): ("8", "*"),
                    _kc("KEY_9"): ("9", "("),
                    _kc("KEY_0"): ("0", ")"),
                    _kc("KEY_MINUS"): ("-", "_"),
                    _kc("KEY_EQUAL"): ("=", "+"),
                    _kc("KEY_GRAVE"): ("'", "\""),
                    _kc("KEY_SLASH"): (".", ","),
                },
            },
        }
        self._mappable_keys = set()
        for layout in self._layouts.values():
            self._mappable_keys.update(layout["letters"].keys())
            self._mappable_keys.update(layout["non_letters"].keys())
        self._mappable_keys.update(
            {
                _kc("KEY_SPACE"),
                _kc("KEY_ENTER"),
                _kc("KEY_KPENTER"),
            }
        )

    def to_char(self, keycode: int, shift: bool, caps: bool, layout: str) -> str | None:
        if layout not in self._layouts:
            return None
        letters = self._layouts[layout]["letters"]
        if keycode in letters:
            base = letters[keycode]
            use_upper = shift ^ caps
            return base.upper() if use_upper else base
        non_letters = self._layouts[layout]["non_letters"]
        if keycode in non_letters:
            base, shifted = non_letters[keycode]
            return shifted if shift else base
        if keycode == _kc("KEY_SPACE"):
            return " "
        if keycode in (_kc("KEY_ENTER"), _kc("KEY_KPENTER")):
            return "\n"
        return None

    def is_mappable(self, keycode: int) -> bool:
        return keycode in self._mappable_keys
