from __future__ import annotations

from typing import Any, Dict


def get_mile_orders(date_from: str, date_to: str, ds: str | None = None) -> Dict[str, Any]:
    """
    Возвращает сырые или агрегированные данные по мили.
    Реализация внутри backend: SQL к analytics DB.
    """
    raise NotImplementedError


def get_courier_stats(date_from: str, date_to: str, ds: str | None = None) -> Dict[str, Any]:
    """
    Возвращает агрегированную статистику по курьерам.
    Реализация внутри backend: SQL к analytics DB.
    """
    raise NotImplementedError


def get_ziz_stats(date_from: str, date_to: str, ds: str | None = None) -> Dict[str, Any]:
    """
    Возвращает статистику по ЗиЗ.
    Реализация внутри backend: SQL к analytics DB.
    """
    raise NotImplementedError


def get_quality_stats(date_from: str, date_to: str, ds: str | None = None) -> Dict[str, Any]:
    """
    Возвращает агрегированную статистику по качеству доставки.
    Реализация внутри backend: SQL к analytics DB.
    """
    raise NotImplementedError

