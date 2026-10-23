# -*- coding: utf-8 -*-
"""
Serve the Morteza Management Software app so a phone can open it and add it to the
home screen.

WHY THIS EXISTS
---------------
Chrome (Android) will not install a web app from a file:// URL, and it also refuses
plain http://192.168.x.x. For the real "install / add to home screen" (a standalone
app window with an icon) Chrome requires a *trustworthy* HTTPS origin.

This script can serve the folder in two ways:

  python serve.py                -> plain http, fine for a quick look on this PC
  python serve.py --https        -> https with a local certificate (desktop testing)

For --https it creates a small local Certificate Authority plus a server
certificate that covers this PC's LAN address, and you install `certs/apartment-ca.crt`
once to make that certificate trusted.

BEWARE: --https is NOT a reliable way to install the app on an Android phone.
Chrome on Android keeps its own certificate store and requires Certificate
Transparency, so a CA you created yourself is normally rejected there no matter
what you install. --https is handy for testing on this PC. For a real
"add to home screen" install on the phone, host this folder on a normal HTTPS
address (see README.md).

Nothing is uploaded anywhere; everything stays on your own Wi-Fi.
"""
from __future__ import annotations

import argparse
import http.server
import os
import shutil
import socket
import socketserver
import subprocess
import sys
from functools import partial

# Windows consoles are often cp1252; the Persian banner must not crash the server.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(HERE, "certs")

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}


class Handler(http.server.SimpleHTTPRequestHandler):
    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in TYPES:
            return TYPES[ext]
        return super().guess_type(path)

    def end_headers(self):
        low = self.path.split("?")[0]
        if low.endswith((".html", ".webmanifest", "/")) or low == "":
            self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Service-Worker-Allowed", "/")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s - %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def lan_ips():
    ips = []
    for probe in (("8.8.8.8", 80), ("1.1.1.1", 80)):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(probe)
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
        except Exception:
            pass
        finally:
            s.close()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips


def find_openssl():
    found = shutil.which("openssl")
    if found:
        return found
    candidates = [
        r"C:\Program Files\OpenSSL-Win64\bin\openssl.exe",
        r"C:\Program Files\Git\usr\bin\openssl.exe",
        os.path.join(os.path.dirname(sys.executable), "Library", "bin", "openssl.exe"),
        os.path.join(os.path.dirname(sys.executable), "Scripts", "openssl.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def make_certs(ips):
    """Create a local CA + server cert covering localhost and the LAN addresses."""
    os.makedirs(CERT_DIR, exist_ok=True)
    crt = os.path.join(CERT_DIR, "apartment-server.crt")
    key = os.path.join(CERT_DIR, "apartment-server.key")
    ca_crt = os.path.join(CERT_DIR, "apartment-ca.crt")
    if os.path.exists(crt) and os.path.exists(key) and os.path.exists(ca_crt):
        return crt, key, ca_crt, True

    openssl = find_openssl()
    if not openssl:
        print("\n!! openssl was not found, so --https cannot create a certificate.")
        print("   Either run without --https, or host the folder on any HTTPS site.\n")
        return None, None, None, False

    ca_key = os.path.join(CERT_DIR, "apartment-ca.key")
    alt = ["DNS:localhost", "IP:127.0.0.1", "IP:::1"]
    for ip in ips:
        alt.append("IP:" + ip)

    ca_cnf = os.path.join(CERT_DIR, "ca.cnf")
    srv_cnf = os.path.join(CERT_DIR, "server.cnf")
    with open(ca_cnf, "w", encoding="utf-8") as f:
        f.write(
            "[req]\ndistinguished_name=dn\nx509_extensions=v3\nprompt=no\n"
            "[dn]\nCN=Apartment Charge Local CA\nO=Apartment Charge\n"
            "[v3]\nbasicConstraints=critical,CA:TRUE,pathlen:0\n"
            "keyUsage=critical,keyCertSign,cRLSign\n"
        )
    with open(srv_cnf, "w", encoding="utf-8") as f:
        f.write(
            "[req]\ndistinguished_name=dn\nprompt=no\n"
            "[dn]\nCN=apartment-charge.local\nO=Apartment Charge\n"
            "[v3]\nbasicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth\n"
            "subjectAltName=" + ",".join(alt) + "\n"
        )

    def run(args):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stdout[-800:])
            print(r.stderr[-800:])
            raise SystemExit("openssl failed")

    csr = os.path.join(CERT_DIR, "server.csr")
    run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
         "-config", ca_cnf, "-keyout", ca_key, "-out", ca_crt])
    run([openssl, "req", "-newkey", "rsa:2048", "-nodes", "-config", srv_cnf, "-keyout", key, "-out", csr])
    run([openssl, "x509", "-req", "-in", csr, "-CA", ca_crt, "-CAkey", ca_key,
         "-CAcreateserial", "-days", "825", "-extfile", srv_cnf, "-extensions", "v3", "-out", crt])
    try:
        os.remove(csr)
    except OSError:
        pass
    return crt, key, ca_crt, False


def main():
    ap = argparse.ArgumentParser(description="Serve the apartment-charge PWA.")
    ap.add_argument("--port", type=int, default=8443)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--https", action="store_true", help="serve over https (needed for install)")
    args = ap.parse_args()

    ips = lan_ips()
    scheme = "http"
    if args.https:
        crt, key, ca_crt, reused = make_certs(ips)
        if not crt:
            return 1
        scheme = "https"
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(crt, key)

    handler = partial(Handler, directory=HERE)
    try:
        httpd = Server((args.host, args.port), handler)
    except OSError as e:
        print("\n!! Could not start on port %d: %s" % (args.port, e))
        print("   Another program is using it. Retry with:  python serve.py --port %d\n" % (args.port + 1))
        return 1
    if args.https:
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    line = "=" * 64
    print("\n" + line)
    print("  \u0634\u0627\u0631\u0698 \u0622\u067e\u0627\u0631\u062a\u0645\u0627\u0646 \u2014 \u0633\u0631\u0648\u0631 \u0631\u0648\u0634\u0646 \u0634\u062f  (%s)" % scheme)
    print(line)
    print("  \u0627\u06cc\u0646 \u0622\u062f\u0631\u0633 \u0631\u0627 \u062f\u0631 \u0645\u0631\u0648\u0631\u06af\u0631 \u06af\u0648\u0634\u06cc \u0628\u0627\u0632 \u06a9\u0646\u06cc\u062f")
    print("  (\u06af\u0648\u0634\u06cc \u0648 \u0627\u06cc\u0646 \u06a9\u0627\u0645\u067e\u06cc\u0648\u062a\u0631 \u0631\u0648\u06cc \u06cc\u06a9 \u0648\u0627\u06cc\u200c\u0641\u0627\u06cc \u0628\u0627\u0634\u0646\u062f):\n")
    if ips:
        for ip in ips:
            print("      %s://%s:%d/" % (scheme, ip, args.port))
    else:
        print("      %s://<IP \u06a9\u0627\u0645\u067e\u06cc\u0648\u062a\u0631>:%d/" % (scheme, args.port))
    print("\n      %s://localhost:%d/    (\u0641\u0642\u0637 \u0631\u0648\u06cc \u062e\u0648\u062f \u0627\u06cc\u0646 \u06a9\u0627\u0645\u067e\u06cc\u0648\u062a\u0631)" % (scheme, args.port))
    if args.https:
        print("\n  \u0645\u0647\u0645: \u0628\u0631\u0627\u06cc \u0627\u06cc\u0646\u06a9\u0647 \u06af\u0648\u0634\u06cc \u0627\u06cc\u0646 \u06af\u0648\u0627\u0647\u06cc \u0631\u0627 \u0642\u0628\u0648\u0644 \u06a9\u0646\u062f\u060c \u06cc\u06a9\u200c\u0628\u0627\u0631 \u0641\u0627\u06cc\u0644")
        print("        certs\\apartment-ca.crt")
        print("  \u0631\u0627 \u0631\u0648\u06cc \u06af\u0648\u0634\u06cc \u062a\u0646\u0635\u06cc\u0628 \u06a9\u0646\u06cc\u062f \u2014 \u062a\u0648\u0636\u06cc\u062d \u06a9\u0627\u0645\u0644 \u062f\u0631 README.md")
    else:
        print("\n  \u062a\u0648\u062c\u0647: \u0631\u0648\u06cc http:// \u06cc\u0639\u0646\u06cc \u0622\u062f\u0631\u0633 \u0634\u0628\u06a9\u0647 \u0645\u062d\u0644\u06cc\u060c \u06a9\u0631\u0648\u0645 \u06af\u0632\u06cc\u0646\u0647 \u00ab\u0646\u0635\u0628\u00bb \u0646\u0645\u06cc\u200c\u062f\u0647\u062f.")
        print("  \u0628\u0631\u0627\u06cc \u0646\u0635\u0628 \u0648\u0627\u0642\u0639\u06cc \u0627\u06cc\u0646 \u0631\u0627 \u0628\u0627 --https \u0627\u062c\u0631\u0627 \u06a9\u0646\u06cc\u062f:  python serve.py --https")
    print("\n  \u062a\u0648\u0642\u0641: Ctrl+C")
    print(line + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\u0633\u0631\u0648\u0631 \u062e\u0627\u0645\u0648\u0634 \u0634\u062f.\n")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
