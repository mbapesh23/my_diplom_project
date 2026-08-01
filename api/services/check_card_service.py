import re
from typing import Tuple

def luhn_checksum(card_number: str) -> bool:
    """
    Алгоритм Луна (Luhn algorithm).
    Проверяет контрольную сумму номера карты.
    https://ru.wikipedia.org/wiki/Алгоритм_Луна
    """
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    # Приводим к строке на случай, если придет число
    digits = digits_of(str(card_number))
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
        
    return checksum % 10 == 0


class CardValidationError(Exception):
    """Кастомное исключение для ошибок валидации карты"""
    pass


def validate_card_data(number: str) -> Tuple[bool, str]:
    """
    Полный цикл проверки банковской карты.
    Возвращает кортеж (is_valid: bool, error_message: str).
    Очищает номер от пробелов и дефисов перед проверкой.
    """
    if not number:
        raise CardValidationError("Номер карты не может быть пустым")

    # Удаляем все лишние символы (пробелы, тире)
    clean_number = re.sub(r'[\s-]', '', str(number))

    # Проверка на цифры
    if not clean_number.isdigit():
        raise CardValidationError("Номер карты должен содержать только цифры")

    # Проверка длины (стандарт ISO/IEC 7812)
    if len(clean_number) < 13 or len(clean_number) > 19:
        raise CardValidationError(f"Длина номера карты должна быть от 13 до 19 цифр (у вас {len(clean_number)})")

    # Проверка алгоритмом Луна
    if not luhn_checksum(clean_number):
        raise CardValidationError("Невалидный номер карты (ошибка контрольной суммы)")

    return True, ""