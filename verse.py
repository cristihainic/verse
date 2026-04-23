#!/usr/bin/env python3
"""Daily Bible verse in your terminal, served instantly from a local cache."""
import argparse
import fcntl
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen

POOL_SIZE = 30
URL = "https://dailyverses.net/random-bible-verse"
SCRIPT_URL = "https://raw.githubusercontent.com/cristihainic/verse/master/verse.py"
DEPS = ["beautifulsoup4>=4.12", "requests>=2.31"]
BEZEL = "\n" + "#" * 50 + "\n"
ERR_MSG = f"{BEZEL}Could not fetch daily verse. No internet? Hiccups on dailyverses.net?{BEZEL}"


def ensure_deps() -> None:
    try:
        import bs4  # noqa: F401
        import requests  # noqa: F401
        return
    except ImportError:
        pass
    print("Installing dependencies (beautifulsoup4, requests)...")
    attempts = [
        [sys.executable, "-m", "pip", "install", "--user", *DEPS],
        [sys.executable, "-m", "pip", "install", "--user", "--break-system-packages", *DEPS],
    ]
    for cmd in attempts:
        try:
            subprocess.check_call(cmd)
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    print("Could not install dependencies automatically. Run:")
    print(f"  {sys.executable} -m pip install --user {' '.join(DEPS)}")
    sys.exit(1)


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    d = Path(base) / "verse"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pool_path() -> Path:
    return cache_dir() / "pool.json"


def lock_path() -> Path:
    return cache_dir() / "refill.lock"


def fetch_one() -> dict:
    import requests
    from bs4 import BeautifulSoup

    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, features="html.parser")
    return {
        "text": soup.find_all("span", "v1")[0].get_text(),
        "source": soup.find_all("a", "vc")[0].get_text(),
    }


def format_verse(v: dict) -> str:
    return f"{BEZEL}{v['text']} ({v['source']}){BEZEL}"


def load_pool() -> list:
    p = pool_path()
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_pool(pool: list) -> None:
    p = pool_path()
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".pool.", suffix=".json")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(pool, f)
        os.replace(tmp, p)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def pop_verse():
    pool = load_pool()
    if not pool:
        return None
    v = pool.pop(0)
    save_pool(pool)
    return v


def spawn_refill_from(script_path: str) -> None:
    """Spawn a detached background process that refills the pool."""
    try:
        subprocess.Popen(
            [sys.executable, script_path, "--refill"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError:
        pass


def do_refill() -> None:
    lock = open(lock_path(), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    try:
        pool = load_pool()
        while len(pool) < POOL_SIZE:
            try:
                pool.append(fetch_one())
                save_pool(pool)
            except Exception:
                break
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def do_default() -> None:
    v = pop_verse()
    if v is None:
        try:
            v = fetch_one()
        except Exception:
            print(ERR_MSG)
            return
    print(format_verse(v))
    if len(load_pool()) < POOL_SIZE:
        spawn_refill_from(os.path.abspath(__file__))


def detect_shell_rc() -> Path:
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return home / ".zshrc"
    if "bash" in shell:
        if sys.platform == "darwin":
            bp = home / ".bash_profile"
            if bp.exists():
                return bp
        return home / ".bashrc"
    for cand in (".zshrc", ".bashrc", ".bash_profile"):
        p = home / cand
        if p.exists():
            return p
    return home / ".profile"


MARKER = "# verse - daily bible verse on terminal start"
RC_LINE = '[ -n "$PS1" ] && command -v verse >/dev/null 2>&1 && verse'


def script_source() -> bytes:
    """Return our own source, either from __file__ or by downloading it."""
    try:
        here = Path(os.path.abspath(__file__))
        if here.is_file() and here.suffix == ".py":
            return here.read_bytes()
    except NameError:
        pass
    with urlopen(SCRIPT_URL) as r:
        return r.read()


def do_install() -> None:
    ensure_deps()

    target_dir = Path.home() / ".local" / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "verse"
    target.write_bytes(script_source())
    target.chmod(0o755)
    print(f"Installed verse to {target}")

    rc = detect_shell_rc()
    rc_text = rc.read_text() if rc.exists() else ""
    if MARKER not in rc_text:
        with rc.open("a") as f:
            if rc_text and not rc_text.endswith("\n"):
                f.write("\n")
            f.write(f"\n{MARKER}\n{RC_LINE}\n")
        print(f"Added verse startup line to {rc}")
    else:
        print(f"Startup line already present in {rc}")

    path_entries = os.environ.get("PATH", "").split(":")
    if str(target_dir) not in path_entries:
        print(f"\nNote: {target_dir} is not on your $PATH.")
        print(f"Add this to {rc} and reopen your terminal:")
        print(f'  export PATH="{target_dir}:$PATH"')

    print("Priming verse pool in the background...")
    spawn_refill_from(str(target))
    print("Done. Open a new terminal to see your first verse.")


def remove_rc_block(rc: Path) -> bool:
    if not rc.exists():
        return False
    lines = rc.read_text().splitlines(keepends=True)
    out = []
    removed = False
    skip_next = 0
    for line in lines:
        if skip_next > 0:
            skip_next -= 1
            removed = True
            continue
        if line.strip() == MARKER:
            skip_next = 1
            removed = True
            continue
        out.append(line)
    if removed:
        rc.write_text("".join(out))
    return removed


def do_uninstall() -> None:
    import shutil

    target = Path.home() / ".local" / "bin" / "verse"
    if target.exists():
        target.unlink()
        print(f"Removed {target}")
    else:
        print(f"No binary at {target}")

    cache = Path(os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")) / "verse"
    if cache.exists():
        shutil.rmtree(cache)
        print(f"Removed {cache}")

    for rc_name in (".zshrc", ".bashrc", ".bash_profile", ".profile"):
        rc = Path.home() / rc_name
        if remove_rc_block(rc):
            print(f"Removed startup line from {rc}")

    print("\nUninstalled. The Python packages beautifulsoup4 and requests were left in place.")
    print("Remove them with: pip uninstall beautifulsoup4 requests")


def main() -> None:
    ap = argparse.ArgumentParser(description="Daily Bible verse in your terminal.")
    ap.add_argument("--install", action="store_true", help="Install verse and wire it into your shell.")
    ap.add_argument("--uninstall", action="store_true", help="Remove verse and its shell startup line.")
    ap.add_argument("--refill", action="store_true", help="(Internal) Refill the verse pool.")
    args = ap.parse_args()
    if args.install:
        do_install()
    elif args.uninstall:
        do_uninstall()
    elif args.refill:
        do_refill()
    else:
        do_default()


if __name__ == "__main__":
    main()
