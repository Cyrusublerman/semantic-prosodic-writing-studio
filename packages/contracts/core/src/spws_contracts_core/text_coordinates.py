from __future__ import annotations


def code_point_to_utf16_index(text: str, code_point_index: int) -> int:
    if code_point_index < 0 or code_point_index > len(text):
        raise ValueError("code-point index out of range")
    return len(text[:code_point_index].encode("utf-16-le")) // 2


def utf16_to_code_point_index(text: str, utf16_index: int) -> int:
    if utf16_index < 0:
        raise ValueError("UTF-16 index out of range")
    current = 0
    for index, character in enumerate(text):
        if current == utf16_index:
            return index
        width = 2 if ord(character) > 0xFFFF else 1
        if current < utf16_index < current + width:
            raise ValueError("UTF-16 index splits a surrogate pair")
        current += width
    if current == utf16_index:
        return len(text)
    raise ValueError("UTF-16 index out of range")


