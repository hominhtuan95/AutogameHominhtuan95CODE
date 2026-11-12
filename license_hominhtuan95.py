"""Xác thực giấy phép ngoại tuyến bằng chữ ký Ed25519."""
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys
import winreg
from datetime import date

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# Được thay bởi setup_license.py trên máy chủ phần mềm.
PUBLIC_KEY_HEX = 'ecb23a1c73f01dce9b21edad1bb0e50dee208bd4f073d28b7c70e4e4c411e158'
APP_ID = 'Hominhtuan95-4CuaSo-v1'


def machine_id():
    # MachineGuid là định danh hệ điều hành Windows; chỉ chia sẻ bản băm.
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography',
                        0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
        guid = str(winreg.QueryValueEx(key, 'MachineGuid')[0]).strip().lower()
    digest = hashlib.sha256((APP_ID + ':' + guid).encode('utf-8')).hexdigest().upper()
    return '-'.join(digest[i:i+8] for i in range(0, 32, 8))


def license_path():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Hominhtuan95'
    base.mkdir(parents=True, exist_ok=True)
    return base / 'license.key'


def validate(code):
    try:
        if len(PUBLIC_KEY_HEX) != 64:
            return False, 'Chưa cấu hình khóa công khai.'
        token = ''.join(code.split())
        raw = base64.urlsafe_b64decode(token + '=' * (-len(token) % 4))
        if len(raw) < 65:
            return False, 'Mã kích hoạt không hợp lệ.'
        payload, signature = raw[:-64], raw[-64:]
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(PUBLIC_KEY_HEX)).verify(signature, payload)
        data = json.loads(payload.decode('utf-8'))
        if data.get('app') != APP_ID or data.get('hwid') != machine_id():
            return False, 'Mã kích hoạt không thuộc máy tính này.'
        expiry = data.get('expiry')
        if expiry is not None and date.fromisoformat(expiry) < date.today():
            return False, 'Mã kích hoạt đã hết hạn.'
        return True, 'Đã kích hoạt.'
    except (ValueError, KeyError, InvalidSignature, UnicodeError, json.JSONDecodeError):
        return False, 'Mã kích hoạt không hợp lệ.'
    except OSError as e:
        return False, 'Không thể đọc mã máy: ' + str(e)


def is_activated():
    try:
        return validate(license_path().read_text(encoding='utf-8'))[0]
    except OSError:
        return False


def save_license(code):
    ok, msg = validate(code)
    if ok:
        license_path().write_text(''.join(code.split()), encoding='utf-8')
    return ok, msg
