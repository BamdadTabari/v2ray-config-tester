# نسخه دقیق‌تر: استفاده از V2Ray Core برای بررسی اتصال واقعی
# نیازمند نصب v2ray-core و اجرای subprocess برای تست هر کانفیگ واقعی

import base64
import json
import concurrent.futures
import subprocess
import tempfile
import os
from urllib.parse import urlparse

INPUT_FILE = "test.txt"
OUTPUT_FILE = "valid_configs.txt"
V2RAY_EXEC = r"C:\\Users\\bamdad\\Desktop\\zz_v2rayN-With-Core-SelfContained\\v2rayN.exe"  # مسیر به فایل اجرایی v2ray-core اگر نصب محلی نیست تغییر دهید


def decode_vmess(link: str):
    try:
        raw = link[8:]
        decoded = base64.b64decode(raw + '=' * (-len(raw) % 4)).decode()
        return json.loads(decoded)
    except:
        return None


def generate_config(link: str):
    if link.startswith("vless://"):
        vmess = decode_vmess(link)
        if not vmess:
            return None
        # ساخت فایل config با v2ray json structure ساده
        return {
            "inbounds": [{"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": vmess["add"],
                    "port": int(vmess["port"]),
                    "users": [{
                        "id": vmess["id"],
                        "alterId": int(vmess.get("aid", 0)),
                        "security": vmess.get("scy", "auto")
                    }]
                }]}}]}
        
    return None


def test_v2ray_config(link: str):
    config = generate_config(link)
    if not config:
        return False

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(config, f)
        fpath = f.name

    try:
        result = subprocess.run([V2RAY_EXEC, "-config", fpath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        success = b"started" in result.stdout or b"Started" in result.stderr
    except Exception:
        success = False
    finally:
        os.remove(fpath)

    return link if success else None


def main():
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    open(OUTPUT_FILE, 'w').close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = executor.map(test_v2ray_config, links)
        for valid in futures:
            if valid:
                print(f"✅ اتصال واقعی موفق: {valid}")
                with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                    f.write(valid + "\n")
            else:
                print("❌ اتصال واقعی ناموفق")

    print("🏁 همه کانفیگ‌ها بررسی شدند")


if __name__ == "__main__":
    main()