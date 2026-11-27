"""Save IBKR's public short-stock list (ftp2.interactivebrokers.com, user shortstock) around the US open.
snap/YYYY-MM-DD/pre.csv.gz  = latest copy taken before 9:30 New York
snap/YYYY-MM-DD/post.csv.gz = first copy taken at/after 9:30 (up to 10:30)
Columns: sym, fee (annual %), available (shares). Stocks missing from the list cannot be shorted at IBKR."""
import urllib.request, gzip, io, csv, re, sys, os
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

now = datetime.now(ZoneInfo("America/New_York"))
NYSE_CLOSED = {  # full-day US market holidays (half days trade normally)
    "2026-11-26", "2026-12-25", "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
    "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24"}
TEST = os.environ.get("TEST") == "1"   # manual check: fetch and count only
if (now.weekday() >= 5 or now.strftime("%Y-%m-%d") in NYSE_CLOSED) and not TEST:
    sys.exit("market closed")
m = now.hour * 60 + now.minute
if (m < 8 * 60 or m > 10 * 60 + 30) and not TEST:
    sys.exit("outside window")
kind = "pre" if m < 9 * 60 + 30 else "post"
d = Path("snap") / now.strftime("%Y-%m-%d"); d.mkdir(parents=True, exist_ok=True)
f = d / f"{kind}.csv.gz"
if kind == "post" and f.exists():
    sys.exit("post already saved")
raw = None
for _ in range(5):
    try:
        raw = urllib.request.urlopen("ftp://shortstock:@ftp2.interactivebrokers.com/usa.txt", timeout=120).read().decode("latin-1")
        break
    except Exception as e:
        print("retry", e)
if raw is None:
    sys.exit(1)
lines = raw.splitlines()
if TEST:
    sys.exit(f"TEST ok: {len(lines)} lines, header {lines[0]}")
stamp = lines[0].split("|")[1:3]
out = io.StringIO(); w = csv.writer(out)
w.writerow(["sym", "fee", "available", "file_time", "saved_ny"])
n = 0
for ln in lines[2:]:
    p = ln.split("|")
    if len(p) < 8 or not re.fullmatch(r"[A-Z]{1,5}(\.[A-Z])?", p[0]):
        continue
    w.writerow([p[0], p[6], p[7].lstrip(">"), " ".join(stamp), now.strftime("%H:%M")]); n += 1
f.write_bytes(gzip.compress(out.getvalue().encode()))
print(kind, f, n, "symbols, file time", stamp)
