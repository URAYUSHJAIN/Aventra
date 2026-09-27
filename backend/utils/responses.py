"""Shared response envelope and input validation for all routes.

Success: {"success": true, "data": ...}. Failure: {"success": false, "error": "<human-readable message>"}.
"""
from __future__ import annotations

from flask import jsonify

from ml.data.assets import get_asset, normalize_symbol


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def ok(data, status: int = 200):
    return jsonify(success=True, data=data), status


def fail(message: str, status: int):
    return jsonify(success=False, error=message), status


def require_symbol(raw: str | None, analysed_only: bool = False) -> str:
    symbol = normalize_symbol(raw or "")
    if symbol is None:
        raise ApiError("A valid symbol is required (letters, digits, &, -, . or ^; at most 20 characters).", 400)
    if analysed_only and get_asset(symbol) is None:
        raise ApiError(f"{symbol} is not in Aventra's analysed asset universe.", 404)
    return symbol


def int_arg(value: str | None, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except ValueError as error:
        raise ApiError("Numeric query parameters must be integers.", 400) from error
    return max(minimum, min(maximum, number))
