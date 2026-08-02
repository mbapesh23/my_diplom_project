from typing import Optional

def luhn_check(card_number: str) -> bool:
    """
    Простая валидация номера карты по алгоритму Луна.
    """
    card_number = card_number.replace(" ", "")
    if not card_number.isdigit():
        return False
    total = 0
    reverse_digits = card_number[::-1]
    for i, ch in enumerate(reverse_digits):
        digit = int(ch)
        if i % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def check_card(card_number: str) -> bool:
    """
    Простой сервис-метод; возвращает True если номер валиден по Луну.
    """
    return luhn_check(card_number)