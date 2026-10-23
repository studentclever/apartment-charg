# -*- coding: utf-8 -*-
"""
Share this folder on an https address (no signup, no upload).

How it works:
  1) a small local server serves the app from this computer
  2) an ssh tunnel to localhost.run exposes it as a temporary https address
  3) open the printed address on the phone, then Chrome menu -> "Install app"

Run:
    python share_https.py

The address is temporary and dies with this window, but the app already installed
on the phone keeps working offline. All data stays on the phone itself.
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import functools

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# When output is piped or redirected, keep the banner visible line by line.
print = functools.partial(print, flush=True)

HERE = os.path.dirname(os.path.abspath(__file__))
TUNNEL_HOST = "nokey@localhost.run"


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def ensure_key():
    """Create a throwaway ssh key the first time; reuse it afterwards."""
    keygen = shutil.which("ssh-keygen")
    if not keygen:
        return None, "ssh-keygen not found"
    # Keep the private key outside the app folder so it can never be uploaded
    # along with the app to a hosting service.
    keydir = os.path.join(os.environ.get("TEMP", HERE), "apartment-charge-tunnel")
    try:
        os.makedirs(keydir, exist_ok=True)
    except OSError:
        keydir = HERE
    key = os.path.join(keydir, "tunnel_key")
    if os.path.exists(key):
        return key, None
    r = subprocess.run(
        [keygen, "-t", "ed25519", "-N", "", "-f", key, "-q", "-C", "apartment-charge"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return None, (r.stderr or "").strip() or "ssh-keygen failed"
    return key, None


def main():
    ssh = shutil.which("ssh")
    if not ssh:
        print("\n!! ssh was not found. On Windows 10/11 enable it via")
        print("   Settings > Apps > Optional features > OpenSSH Client\n")
        return 1

    key, err = ensure_key()
    if not key:
        print("\n!! could not create the temporary key: %s\n" % err)
        return 1

    port = free_port()
    print("\n" + "=" * 60)
    print("  \u0633\u0631\u0648\u0631 \u0645\u062d\u0644\u06cc \u0631\u0648\u06cc \u067e\u0648\u0631\u062a %d \u0631\u0648\u0634\u0646 \u0645\u06cc\u200c\u0634\u0648\u062f..." % port)
    print("=" * 60 + "\n")

    server = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "serve.py"),
         "--port", str(port), "--host", "127.0.0.1"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )

    log = []
    url_box = {"url": None}
    done = threading.Event()

    def pump(proc):
        for line in proc.stdout:
            log.append(line.rstrip())
            if url_box["url"] is None:
                m = re.search(r"https://[a-z0-9-]+\.lhr\.life", line)
                if m:
                    url_box["url"] = m.group(0)
                    done.set()

    threading.Thread(target=pump, args=(server,), daemon=True).start()
    time.sleep(3.0)

    tunnel = subprocess.Popen(
        [ssh, "-i", key,
         "-o", "StrictHostKeyChecking=no",
         "-o", "UserKnownHostsFile=NUL",
         "-o", "ServerAliveInterval=15",
         "-R", "80:127.0.0.1:%d" % port, TUNNEL_HOST],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )
    threading.Thread(target=pump, args=(tunnel,), daemon=True).start()

    done.wait(timeout=60)
    url = url_box["url"]

    print("=" * 60)
    if url:
        print("  \u0622\u062f\u0631\u0633 https \u0622\u0645\u0627\u062f\u0647 \u0627\u0633\u062a (\u0647\u0645\u06cc\u0646 \u0631\u0627 \u0631\u0648\u06cc \u06af\u0648\u0634\u06cc \u0628\u0627\u0632 \u06a9\u0646\u06cc\u062f):")
        print("\n      %s\n" % url)
        print("  \u062f\u0631 \u06a9\u0631\u0648\u0645 \u06af\u0648\u0634\u06cc: \u0645\u0646\u0648\u06cc \u22ee  \u2190  \u00ab\u0646\u0635\u0628 \u0628\u0631\u0646\u0627\u0645\u0647\u00bb")
        print("  \u0627\u06af\u0631 \u0627\u06cc\u0646 \u06af\u0632\u06cc\u0646\u0647 \u0631\u0627 \u0646\u062f\u06cc\u062f\u06cc\u062f\u060c \u0635\u0641\u062d\u0647 \u0631\u0627 \u06cc\u06a9\u200c\u0628\u0627\u0631 \u0628\u0628\u0646\u062f\u06cc\u062f \u0648 \u062f\u0648\u0628\u0627\u0631\u0647 \u0628\u0627\u0632 \u06a9\u0646\u06cc\u062f.")
    else:
        print("  !! \u0622\u062f\u0631\u0633 https \u0633\u0627\u062e\u062a\u0647 \u0646\u0634\u062f. \u0645\u062a\u0646 \u0632\u06cc\u0631 \u0631\u0627 \u0628\u0631\u0627\u06cc \u067e\u0634\u062a\u06cc\u0628\u0627\u0646\u06cc \u0646\u06af\u0647 \u062f\u0627\u0631\u06cc\u062f:\n")
        print("\n".join(log[-15:]))
    print("=" * 60)
    print("\n  \u0628\u0631\u0627\u06cc \u067e\u0627\u06cc\u0627\u0646: Ctrl+C\n")

    try:
        while True:
            if server.poll() is not None:
                print("\n!! \u0633\u0631\u0648\u0631 \u0645\u062d\u0644\u06cc \u0628\u0633\u062a\u0647 \u0634\u062f:\n")
                print("\n".join(log[-15:]))
                break
            if tunnel.poll() is not None:
                print("\n!! \u062a\u0648\u0646\u0644 \u0628\u0633\u062a\u0647 \u0634\u062f:\n")
                print("\n".join(log[-15:]))
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in (tunnel, server):
            try:
                p.terminate()
            except Exception:
                pass
        print("\n\u067e\u0627\u06cc\u0627\u0646 \u06cc\u0627\u0641\u062a.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
