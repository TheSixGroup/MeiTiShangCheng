# -*- coding: utf-8 -*-
"""诊断 Python 出网：DNS / TCP(IPv4,IPv6) / TLS / HTTPS 逐层测试。"""
import socket
import ssl
import time

HOST = "pypi.tuna.tsinghua.edu.cn"
PORT = 443
TIMEOUT = 5


def now(t0):
    return round(time.time() - t0, 2)


print(f"target: https://{HOST}/simple/")
print("-" * 52)

# 1) DNS
t0 = time.time()
infos = []
try:
    infos = socket.getaddrinfo(HOST, PORT, proto=socket.IPPROTO_TCP)
    print(f"DNS      OK    {now(t0):>6}s   {len(infos)} 条记录")
    for fam, _, _, _, addr in infos[:6]:
        kind = "IPv6" if fam == socket.AF_INET6 else "IPv4"
        print(f"              {kind}  {addr[0]}")
except Exception as e:
    print(f"DNS      FAIL  {now(t0):>6}s   {e}")

# 2) TCP（分别测 IPv4 / IPv6）
for fam, _, _, _, addr in infos[:6]:
    kind = "IPv6" if fam == socket.AF_INET6 else "IPv4"
    t0 = time.time()
    try:
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect(addr)
        s.close()
        print(f"TCP-{kind}  OK    {now(t0):>6}s   {addr[0]}:{PORT}")
    except Exception as e:
        print(f"TCP-{kind}  FAIL  {now(t0):>6}s   {addr[0]}  {type(e).__name__}: {e}")

# 3) TLS 握手
t0 = time.time()
try:
    ctx = ssl.create_default_context()
    with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as sock:
        with ctx.wrap_socket(sock, server_hostname=HOST) as ss:
            print(f"TLS      OK    {now(t0):>6}s   {ss.version()}")
except Exception as e:
    print(f"TLS      FAIL  {now(t0):>6}s   {type(e).__name__}: {e}")

# 4) HTTPS GET（和 pip 做的完全一样）
t0 = time.time()
try:
    import urllib.request

    with urllib.request.urlopen(f"https://{HOST}/simple/flask/", timeout=TIMEOUT) as r:
        print(f"HTTPS    OK    {now(t0):>6}s   status={r.status}  bytes={len(r.read(200))}")
except Exception as e:
    print(f"HTTPS    FAIL  {now(t0):>6}s   {type(e).__name__}: {e}")

print("-" * 52)
print("结论：DNS/TCP 都 OK 但 TLS 或 HTTPS FAIL → Python 的 TLS 被拦截；")
print("      IPv6 那行 FAIL、IPv4 OK → 强制 IPv4 就能解决。")
