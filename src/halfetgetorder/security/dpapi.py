"""Windows DPAPI — 이 PC·현재 사용자 계정에서만 복호화 가능."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes


class DpapiError(OSError):
    pass


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob_from_bytes(data: bytes) -> _DATA_BLOB:
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))


def _bytes_from_blob(blob: _DATA_BLOB) -> bytes:
    return ctypes.string_at(blob.pbData, blob.cbData)


def protect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise DpapiError("DPAPI는 Windows에서만 사용할 수 있습니다.")
    if not data:
        raise ValueError("빈 데이터는 암호화할 수 없습니다.")

    in_blob = _blob_from_bytes(data)
    out_blob = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise DpapiError("DPAPI 암호화에 실패했습니다.")
    try:
        return _bytes_from_blob(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def unprotect(data: bytes) -> bytes:
    if sys.platform != "win32":
        raise DpapiError("DPAPI는 Windows에서만 사용할 수 있습니다.")
    if not data:
        raise ValueError("복호화할 데이터가 없습니다.")

    in_blob = _blob_from_bytes(data)
    out_blob = _DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise DpapiError("DPAPI 복호화에 실패했습니다. (다른 PC/계정에서 생성된 파일일 수 있습니다)")
    try:
        return _bytes_from_blob(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)
