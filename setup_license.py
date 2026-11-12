"""Chạy 1 lần trên máy chủ Auto. KHÔNG đưa khóa riêng lên GitHub."""
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

folder = Path(__file__).resolve().parent
private_file = folder / 'PRIVATE_LICENSE_KEY.pem'
module = folder / 'license_hominhtuan95.py'
if private_file.exists():
    key = serialization.load_pem_private_key(private_file.read_bytes(), password=None)
    print('Sử dụng khóa riêng đã có.')
else:
    key = Ed25519PrivateKey.generate()
    private_file.write_bytes(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()))
    print('Đã tạo khóa riêng mới.')
public_hex = key.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw).hex()
text = module.read_text(encoding='utf-8')
import re
text, count = re.subn(r"^PUBLIC_KEY_HEX = '[^']*'", f"PUBLIC_KEY_HEX = '{public_hex}'", text, count=1, flags=re.M)
if count != 1:
    raise RuntimeError('Không tìm thấy PUBLIC_KEY_HEX trong license_hominhtuan95.py')
module.write_text(text, encoding='utf-8')
print('Đã cập nhật khóa công khai. Chỉ upload license_hominhtuan95.py, KHÔNG upload PRIVATE_LICENSE_KEY.pem.')
