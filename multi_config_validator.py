import base64
import json
import concurrent.futures
import subprocess
import tempfile
import os
from urllib.parse import urlparse, parse_qs

INPUT_FILE = "test.txt"
OUTPUT_FILE = "valid_configs.txt"
V2RAY_EXEC = r"C:\\Users\\bamdad\\Desktop\\zz_v2rayN-With-Core-SelfContained\\v2rayN.exe"


def decode_vmess(link: str):
    raw = link[8:]
    decoded = base64.b64decode(raw + '=' * (-len(raw) % 4)).decode()
    return json.loads(decoded)


def generate_config(link: str):
    if link.startswith("vmess://"):
        vmess = decode_vmess(link)
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
                }]}
            }]
        }

    if link.startswith("vless://"):
        u = urlparse(link)
        params = parse_qs(u.query)
        return {
            "inbounds": [{"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": u.hostname,
                    "port": int(u.port or 443),
                    "users": [{
                        "id": u.username,
                        "encryption": params.get("encryption", ["none"])[0],
                        "flow": params.get("flow", [None])[0]
                    }]
                }]}
            }]
        }

    if link.startswith("trojan://"):
        u = urlparse(link)
        return {
            "inbounds": [{"port": 1080, "listen": "127.0.0.1", "protocol": "socks", "settings": {"auth": "noauth"}}],
            "outbounds": [{
                "protocol": "trojan",
                "settings": {"servers": [{
                    "address": u.hostname,
                    "port": int(u.port or 443),
                    "password": u.username
                }]}
            }]
        }

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
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found")
        return

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
