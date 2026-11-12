"""Cấp mã trên máy chủ Auto; không chia sẻ file này kèm khóa riêng."""
import argparse
import base64
from datetime import date
import json
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from license_hominhtuan95 import APP_ID

parser = argparse.ArgumentParser(description='Cấp mã kích hoạt Hominhtuan95')
parser.add_argument('--hwid', required=True, help='Mã máy khách gửi')
parser.add_argument('--expiry', default=None, help='Hạn dùng YYYY-MM-DD; bỏ trống = không hết hạn')
args = parser.parse_args()
hwid = args.hwid.strip().upper()
if len(hwid) != 35 or any(c not in '0123456789ABCDEF-' for c in hwid):
    parser.error('HWID không hợp lệ. Ví dụ XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX')
if args.expiry:
    try: date.fromisoformat(args.expiry)
    except ValueError: parser.error('Hạn dùng phải là YYYY-MM-DD')
key_path = Path(__file__).resolve().parent / 'PRIVATE_LICENSE_KEY.pem'
if not key_path.exists():
    parser.error('Chưa có PRIVATE_LICENSE_KEY.pem. Chạy setup_license.py trước.')
key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
payload = json.dumps({'app': APP_ID, 'hwid': hwid, 'expiry': args.expiry},
                     sort_keys=True, separators=(',', ':')).encode('utf-8')
code = base64.urlsafe_b64encode(payload + key.sign(payload)).decode('ascii').rstrip('=')
print('\nMÃ KÍCH HOẠT CHO MÁY', hwid, ':\n')
print(code)
print('\nHạn dùng:', args.expiry or 'Không giới hạn')
