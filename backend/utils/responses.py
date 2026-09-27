"""Shared response envelope and input validation for all routes.

Success: {"success": true, "data": ...}. Failure: {"success": false, "error": "<human-readable message>", "code": "<STATE>"}.
"""
from __future__ import annotations

from flask import jsonify

from ml.instruments import ids


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "BAD_REQUEST"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code


def ok(data, status: int = 200):
    return jsonify(success=True, data=data), status


def fail(message: str, status: int, code: str = "ERROR", **extra):
    return jsonify(success=False, error=message, code=code, **extra), status


def require_instrument_id(raw: str | None, allow_legacy: bool = True) -> str:
    """Canonical instrument ID from user input (legacy bare NSE symbols still resolve, e.g. RELIANCE → XNSE:RELIANCE)."""
    try:
        return str(ids.parse(raw or "", allow_legacy=allow_legacy))
    except ids.InvalidInstrumentId as error:
        raise ApiError(f"{error} Expected an instrument ID such as XNSE:RELIANCE, XNAS:AAPL, CRYPTO:BTC-USDT or FX:USDINR.", 400, "INVALID_INSTRUMENT_ID") from error


def int_arg(value: str | None, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except ValueError as error:
        raise ApiError("Numeric query parameters must be integers.", 400) from error
    return max(minimum, min(maximum, number))


def choice_arg(value: str | None, allowed: set[str], name: str) -> str | None:
    if value in (None, ""):
        return None
    if value not in allowed:
        raise ApiError(f"Unsupported {name} '{value}'.", 400)
    return value
