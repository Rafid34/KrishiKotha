"""Prove that DATA_MODE=snapshot serves the API with no outbound network access.

The script starts a real uvicorn server in a child process with:
  * DATA_MODE=snapshot and an empty temporary database (so all data comes from data/snapshots),
  * every non-loopback socket connection and DNS lookup blocked and logged.
It then calls the read API over HTTP and fails if any blocked attempt was recorded.

This is a process-level block (sockets patched in the server process), not an OS firewall.

Usage: python scripts/verify_offline.py [--port 8765]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}


def _install_network_block(log_path: Path) -> None:
    """Patch `socket` so any connection to a non-loopback host raises and is logged."""

    in_selftest = {"on": False}

    def log(kind: str, target: object) -> None:
        if in_selftest["on"] and kind.startswith("blocked"):
            return  # the self-test's own attempt is recorded as `selftest-blocked`
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{kind} {target}\n")

    def is_local(host: object) -> bool:
        return isinstance(host, (str, bytes)) and (host.decode() if isinstance(host, bytes) else host) in LOCAL_HOSTS

    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def connect(self: socket.socket, address: object) -> None:
        host = address[0] if isinstance(address, tuple) else address
        if not is_local(host):
            log("blocked-connect", address)
            raise OSError(f"network disabled: connect to {address}")
        return real_connect(self, address)  # type: ignore[arg-type]

    def connect_ex(self: socket.socket, address: object) -> int:
        host = address[0] if isinstance(address, tuple) else address
        if not is_local(host):
            log("blocked-connect", address)
            return 10051  # WSAENETUNREACH
        return real_connect_ex(self, address)  # type: ignore[arg-type]

    def getaddrinfo(host: object, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if host is not None and not is_local(host):
            log("blocked-dns", host)
            raise socket.gaierror(f"network disabled: lookup of {host}")
        return real_getaddrinfo(host, *args, **kwargs)  # type: ignore[arg-type]

    socket.socket.connect = connect  # type: ignore[method-assign]
    socket.socket.connect_ex = connect_ex  # type: ignore[method-assign]
    socket.getaddrinfo = getaddrinfo  # type: ignore[assignment]

    # Self-test so a silent no-op patch cannot make the check pass by accident.
    in_selftest["on"] = True
    try:
        socket.create_connection(("example.com", 80), timeout=2)
    except OSError:
        in_selftest["on"] = False
        log("selftest-blocked", "example.com:80")
    else:
        in_selftest["on"] = False
        log("selftest-NOT-BLOCKED", "example.com:80")


def serve(port: int, log_path: Path) -> None:
    """Child process: block the network, then run the FastAPI app with uvicorn."""
    _install_network_block(log_path)
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port, log_level="warning")


def _wait_for_health(base: str, child: subprocess.Popen[bytes], seconds: float = 40.0) -> None:
    import httpx

    deadline = time.time() + seconds
    while time.time() < deadline:
        if child.poll() is not None:
            raise SystemExit(f"server exited early with code {child.returncode}")
        try:
            if httpx.get(f"{base}/api/health", timeout=2.0).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(0.5)
    raise SystemExit("server did not become healthy in time")


def check(base: str) -> list[str]:
    """Call the read API and return a list of failure messages (empty means all passed)."""
    import httpx

    failures: list[str] = []

    def get(path: str) -> httpx.Response:
        return httpx.get(f"{base}{path}", timeout=20.0)

    def expect(ok: bool, message: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {message}")
        if not ok:
            failures.append(message)

    health = get("/api/health").json()
    expect(health["data_mode"] == "snapshot", f"/api/health data_mode={health['data_mode']}")

    latest = get("/api/risk")
    expect(latest.status_code == 200 and len(latest.json()["districts"]) == 8,
           f"/api/risk (latest {latest.json().get('date')}) returns 8 districts")
    event = get("/api/risk?date=2022-06-16")
    body = event.json()
    expect(event.status_code == 200 and len(body["districts"]) == 8, "/api/risk?date=2022-06-16 returns 8 districts")
    sylhet = next((d for d in body["districts"] if d["district_id"] == "sylhet"), None)
    expect(sylhet is not None and sylhet["flood"]["level"] == "high", "Sylhet flood is high on 2022-06-16")
    expect(get("/api/risk?date=2022-06-16&hazard=flood").status_code == 200, "/api/risk hazard filter")
    series = get("/api/risk/sylhet?days=30").json()["series"]
    expect(len(series) == 30, f"/api/risk/sylhet?days=30 returns {len(series)} points")
    explain = get("/api/risk/sylhet/explain?date=2022-06-16").json()
    expect(len(explain["flood"]["inputs"]) == 3, "/api/risk/sylhet/explain lists 3 flood inputs")
    expect(len(get("/api/districts").json()) == 8, "/api/districts returns 8")
    expect(len(get("/api/crops").json()) == 3, "/api/crops returns 3")
    sources = get("/api/sources").json()
    expect(all(s["last_data_date"] for s in sources if s["short_name"] != "GIBS"), "/api/sources has last data dates")
    status = get("/api/pipeline/status").json()
    expect(status["status"] in ("ok", "partial"), f"/api/pipeline/status is {status['status']}")
    return failures


def verify(port: int) -> int:
    """Parent process: spawn the blocked server, run the checks, inspect the block log."""
    with tempfile.TemporaryDirectory(prefix="kk_offline_") as tmp:
        tmp_path = Path(tmp)
        log_path = tmp_path / "network.log"
        env = {
            **os.environ,
            "DATA_MODE": "snapshot",
            "DATABASE_URL": f"sqlite:///{(tmp_path / 'offline.db').as_posix()}",
            "EARTHDATA_USERNAME": "",
            "EARTHDATA_PASSWORD": "",
        }
        cmd = [sys.executable, str(Path(__file__).resolve()), "--serve", "--port", str(port), "--log", str(log_path)]
        child = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env)
        base = f"http://127.0.0.1:{port}"
        try:
            _wait_for_health(base, child)
            print(f"Server up on {base} (DATA_MODE=snapshot, empty database, network blocked)")
            failures = check(base)
        finally:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()

        lines = log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []
        selftest = [ln for ln in lines if ln.startswith("selftest-blocked")]
        attempts = [ln for ln in lines if not ln.startswith("selftest")]
        print(f"Block self-test: {'passed' if selftest else 'FAILED'}; outbound attempts during serving: {len(attempts)}")
        for line in attempts:
            print(f"  {line}")
        if not selftest:
            failures.append("network block self-test failed")
        if attempts:
            failures.append("server attempted outbound network access")

    print("PASS" if not failures else f"FAIL: {json.dumps(failures)}")
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--serve", action="store_true", help="internal: run the blocked server")
    parser.add_argument("--log", type=Path, help="internal: block log path")
    args = parser.parse_args()
    if args.serve:
        sys.path.insert(0, str(REPO_ROOT))
        serve(args.port, args.log)
        return 0
    return verify(args.port)


if __name__ == "__main__":
    sys.exit(main())
