from typing import Optional

from ..check_card import check_card

class CheckCardService:
    """
    Примитивный сервис проверки платежной карты.
    """
    def validate_card(self, card_number: str) -> bool:
        return bool(card_number) and check_card(card_number)