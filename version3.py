import base64
import json
import subprocess
import tempfile
import time
import os
import socket
from urllib.parse import urlparse

INPUT_FILE = "test.txt"
OUTPUT_FILE = "valid_configs.txt"
V2RAY_EXEC = "v2ray.exe"
PING_TEST_DOMAIN = "http://bing.com"
MAX_PING_MS = 10000
SOCKS_PORT = 10808

def decode_vmess(link):
    try:
        raw = link[8:]
        decoded = base64.b64decode(raw + '=' * (-len(raw) % 4)).decode()
        return json.loads(decoded)
    except:
        return None

def extract_vless(link):
    try:
        parsed = urlparse(link)
        return {
            "id": parsed.username,
            "add": parsed.hostname,
            "port": int(parsed.port),
            "type": "vless",
            "tls": "tls" if "tls" in parsed.query else "none",
            "net": "tcp"
        }
    except:
        return None

def extract_trojan(link):
    try:
        parsed = urlparse(link)
        return {
            "password": parsed.username,
            "add": parsed.hostname,
            "port": int(parsed.port),
            "type": "trojan",
            "tls": "tls"
        }
    except:
        return None

def generate_config(config, kind):
    out = {}
    if kind == "vmess":
        out = {
            "outbounds": [{
                "protocol": "vmess",
                "settings": {"vnext": [{
                    "address": config["add"],
                    "port": int(config["port"]),
                    "users": [{
                        "id": config["id"],
                        "alterId": int(config.get("aid", 0)),
                        "security": config.get("scy", "auto")
                    }]
                }]},
                "streamSettings": {
                    "network": config.get("net", "tcp"),
                    "security": config.get("tls", "none"),
                    "wsSettings": {
                        "path": config.get("path", ""),
                        "headers": {"Host": config.get("host", "")}
                    } if config.get("net") == "ws" else {}
                }
            }]
        }
    elif kind == "vless":
        out = {
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{
                    "address": config["add"],
                    "port": int(config["port"]),
                    "users": [{
                        "id": config["id"],
                        "encryption": "none"
                    }]
                }]},
                "streamSettings": {
                    "network": config.get("net", "tcp"),
                    "security": config.get("tls", "none")
                }
            }]
        }
    elif kind == "trojan":
        out = {
            "outbounds": [{
                "protocol": "trojan",
                "settings": {"servers": [{
                    "address": config["add"],
                    "port": int(config["port"]),
                    "password": config["password"]
                }]},
                "streamSettings": {"security": "tls"}
            }]
        }
    out["log"] = {"loglevel": "warning"}
    out["inbounds"] = [{
        "port": SOCKS_PORT,
        "listen": "127.0.0.1",
        "protocol": "socks",
        "settings": {"auth": "noauth"}
    }]
    return out

def wait_for_socks_ready(port=SOCKS_PORT, timeout=1):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except:
            time.sleep(0.5)
    return False

def test_socks_ping():
    try:
        result = subprocess.run([
            "curl", "-s", "-o", "nul",
            "--socks5", f"127.0.0.1:{SOCKS_PORT}",
            "-w", "%{time_total}",
            PING_TEST_DOMAIN
        ], capture_output=True, timeout=2)
        if result.returncode != 0:
            print("⛔ Curl failed:", result.stderr.decode())
            return None
        ms = float(result.stdout.decode().strip()) * 1000
        return ms
    except Exception as e:
        print("⚠️ Error in ping:", e)
        return None

def check_link(link):
    if link.startswith("vmess://"):
        config = decode_vmess(link)
        kind = "vmess"
    elif link.startswith("vless://"):
        config = extract_vless(link)
        kind = "vless"
    elif link.startswith("trojan://"):
        config = extract_trojan(link)
        kind = "trojan"
    else:
        return False

    if not config:
        return False

    full_config = generate_config(config, kind)

    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.json') as tmp:
        json.dump(full_config, tmp, indent=2)
        config_path = tmp.name

    try:
        proc = subprocess.Popen(
            [V2RAY_EXEC, "run", "-config", config_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

        if not wait_for_socks_ready():
            print("❌ SOCKS proxy didn't become ready.")
            proc.terminate()
            return False

        ping = test_socks_ping()
        if ping is not None and ping < MAX_PING_MS:
            print(f"✅ Ping OK: {ping:.0f} ms")
            return True
        else:
            print(f"❌ Ping too high or failed: {ping}")
            return False
    finally:
        proc.terminate()
        os.remove(config_path)

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        links = [line.strip() for line in f if line.strip()]

    valid = []
    for i, link in enumerate(links):
        print(f"⏳ Testing {i+1}/{len(links)}")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(valid))
        if check_link(link):
            valid.append(link)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(valid))

    print(f"\n🟢 Done. Valid configs: {len(valid)} saved in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
