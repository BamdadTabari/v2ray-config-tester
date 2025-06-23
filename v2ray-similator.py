# نسخه دقیق‌تر: استفاده از V2Ray Core برای بررسی اتصال واقعی
# نیازمند نصب v2ray-core و اجرای subprocess برای تست هر کانفیگ واقعی

"""Validate V2Ray links from ``INPUT_FILE``.

Each link is checked without modifying the input file. The script first
verifies connectivity to the remote server then runs V2Ray's config test mode.
Successful links are appended to ``OUTPUT_FILE``.
"""

import base64
import json
import concurrent.futures
import subprocess
import socket
import tempfile
import os
import shutil
from urllib.parse import urlparse

INPUT_FILE = "test.txt"
OUTPUT_FILE = "valid_configs.txt"
# مسیر پیش‌فرض به فایل اجرایی V2Ray در صورت نبود متغیر محیطی
DEFAULT_V2RAY_EXEC = r"C:\\Users\\bamdad\\Desktop\\zz_v2rayN-With-Core-SelfContained\\v2rayN.exe"
V2RAY_EXEC = None


def find_v2ray_exec():
    """Determine V2Ray executable path from env or common locations."""
    env_path = os.environ.get("V2RAY_EXEC")
    if env_path and os.path.isfile(env_path):
        return env_path

    for name in ("v2ray", "v2ray.exe", "v2rayN.exe"):
        path = shutil.which(name)
        if path:
            return path

    if os.path.isfile(DEFAULT_V2RAY_EXEC):
        return DEFAULT_V2RAY_EXEC

    raise FileNotFoundError(
        "V2Ray executable not found. Set V2RAY_EXEC environment variable or update DEFAULT_V2RAY_EXEC."
    )


def decode_vmess(link: str):
    try:
        raw = link[8:]
        decoded = base64.b64decode(raw + '=' * (-len(raw) % 4)).decode()
        return json.loads(decoded)
    except:
        return None


def generate_config(link: str):
    if link.startswith("vmess://"):
        vmess = decode_vmess(link)
        if not vmess:
            return None
        # ساخت فایل config با v2ray json structure ساده
        return {
            "inbounds": [{"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [{
                "protocol": "vmess",
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


def test_v2ray_config(link: str, exec_path: str):
    config = generate_config(link)
    if not config:
        return False

    # quick connectivity check to remote server before spawning V2Ray
    try:
        address = config["outbounds"][0]["settings"]["vnext"][0]["address"]
        port = config["outbounds"][0]["settings"]["vnext"][0]["port"]
        with socket.create_connection((address, port), timeout=5):
            pass
    except Exception:
        return False

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(config, f)
        fpath = f.name

    try:
        # Use V2Ray's built-in config test mode so the process exits immediately
        result = subprocess.run(
            [exec_path, "-test", "-config", fpath],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
        success = result.returncode == 0
    except Exception:
        success = False
    finally:
        os.remove(fpath)

    return link if success else None


def main():
    global V2RAY_EXEC
    V2RAY_EXEC = find_v2ray_exec()
    print(f"Using V2Ray executable: {V2RAY_EXEC}")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        links = [line.strip() for line in f if line.strip()]

    open(OUTPUT_FILE, 'w').close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = executor.map(lambda link: test_v2ray_config(link, V2RAY_EXEC), links)
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
