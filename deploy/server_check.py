#!/usr/bin/env python3
"""Can this server host the app? A quick check, standard library only.

    python3 deploy/server_check.py            # checks, then serves a test page on port 8000
    python3 deploy/server_check.py --port 9000

1. Hardware: GPU (nvidia-smi; torch if installed), CPU, memory, free disk.
2. Outbound internet: Cloudflare (for a tunnel), Ultimate Guitar (tabs),
   Hugging Face and PyPI (models, packages).
3. A test web page on 0.0.0.0:PORT. Open the printed address from a phone or
   laptop: on the same network (does the server accept connections?), then
   on mobile data (is it reachable from outside? usually not, on a college
   network: that is what a tunnel is for). The page measures upload speed:
   pick a song file and press Upload.

To test reaching it from anywhere without a domain or an account, run
Cloudflare's free "quick tunnel" alongside (download cloudflared from
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/):

    cloudflared tunnel --url http://localhost:8000

It prints a https://<random>.trycloudflare.com address: open that on mobile data.
Stop everything with Ctrl+C.
"""

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Server check</title>
<style>body{font:16px system-ui,sans-serif;max-width:560px;margin:40px auto;padding:0 16px}
code{background:#eee;padding:2px 4px}button{font:inherit;padding:8px 16px}</style></head><body>
<h1>&#10004; The server is reachable</h1>
<p>Served by <code>%(host)s</code>. Your device's address as the server sees it: <code>%(client)s</code>.</p>
<h2>Upload speed</h2>
<p>Pick a song file (an MP3 or WAV) and press Upload. Nothing is kept.</p>
<input type="file" id="f"> <button onclick="go()">Upload</button>
<p id="out"></p>
<script>
async function go() {
  const f = document.getElementById("f").files[0];
  if (!f) return;
  const out = document.getElementById("out");
  out.textContent = "Uploading " + (f.size / 1e6).toFixed(1) + " MB ...";
  const t = performance.now();
  const r = await fetch("/upload", {method: "POST", body: f});
  const s = (performance.now() - t) / 1000, j = await r.json();
  out.innerHTML = (j.bytes / 1e6).toFixed(1) + " MB in " + s.toFixed(1) + " s: <b>" +
    (j.bytes / 1e6 / s).toFixed(1) + " MB/s</b> (" + (8 * j.bytes / 1e6 / s).toFixed(0) + " Mbit/s)";
}
</script></body></html>"""


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def hardware():
    print("== Hardware")
    print(f"  {platform.system()} {platform.release()}, Python {platform.python_version()}, {os.cpu_count()} CPU threads")
    try:
        with open("/proc/meminfo") as fh:
            kb = int(fh.readline().split()[1])
        print(f"  memory: {kb / 1e6:.0f} GB")
    except OSError:
        pass
    free = shutil.disk_usage(".").free
    print(f"  free disk here: {free / 1e9:.0f} GB" + ("   (low: songs and models need ~20 GB)" if free < 20e9 else ""))
    gpus = run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"])
    if gpus:
        for line in gpus.splitlines():
            print(f"  GPU: {line}")
    else:
        print("  GPU: nvidia-smi not found or no GPU visible")
    torch = run(["python3", "-c", "import torch; print(torch.__version__, torch.cuda.is_available(), "
                                  "torch.cuda.device_count())"])
    print(f"  torch (version, CUDA available, GPUs): {torch}" if torch else "  torch: not installed for python3 (fine for now)")


def outbound():
    print("== Outbound internet")
    sites = [("Cloudflare (tunnel)", "https://www.cloudflare.com/cdn-cgi/trace"),
             ("Ultimate Guitar (tabs)", "https://tabs.ultimate-guitar.com/"),
             ("Hugging Face (models)", "https://huggingface.co/"),
             ("PyPI (packages)", "https://pypi.org/simple/")]
    public_ip = None
    for name, url in sites:
        t = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 server-check"})
            with urllib.request.urlopen(req, timeout=10) as r:
                body = r.read(4096).decode("utf-8", "replace")
                status = r.status
            print(f"  ok    {name:24} HTTP {status} in {time.time() - t:.1f} s")
            if "cdn-cgi/trace" in url:
                public_ip = dict(l.split("=", 1) for l in body.splitlines() if "=" in l).get("ip")
        except Exception as e:  # noqa: BLE001  any failure is the answer here
            print(f"  FAIL  {name:24} {type(e).__name__}: {e}")
    if public_ip:
        print(f"  this server reaches the internet as {public_ip} (the college's address, usually; not reachable inbound)")


def local_addresses():
    out = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("1.1.1.1", 80))
        out.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    for line in run(["hostname", "-I"]).split():
        if "." in line:
            out.add(line)
    return sorted(out)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (PAGE % {"host": socket.gethostname(), "client": self.client_address[0]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        size, left = 0, int(self.headers.get("Content-Length", 0))
        while left > 0:
            chunk = self.rfile.read(min(left, 1 << 20))
            if not chunk:
                break
            size += len(chunk)
            left -= len(chunk)
        body = json.dumps({"bytes": size}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        print(f"  upload from {self.client_address[0]}: {size / 1e6:.1f} MB")

    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    hardware()
    outbound()
    print("== Test page")
    try:
        server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    except OSError as e:
        raise SystemExit(f"  cannot listen on port {args.port}: {e}. Try --port 9000")
    for ip in local_addresses():
        print(f"  open  http://{ip}:{args.port}   from a phone or laptop on the same network")
    print(f"  then the same address on mobile data; and, for outside access, in another terminal:")
    print(f"        cloudflared tunnel --url http://localhost:{args.port}")
    print("  Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
