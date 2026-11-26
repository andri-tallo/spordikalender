#!/usr/bin/env python3
"""Paneb kokku spordikalender.ics.

Allikad:
  feeds.json   – välised ICS-vood (nt FotMob), laetakse iga käivitusega.
                 Kui laadimine ebaõnnestub, kasutatakse cache/ kausta viimast head koopiat.
  data/*.json  – käsitsi hallatavad sündmused.
                 {"start": "YYYY-MM-DD HH:MM", "tz": "Europe/Tallinn", "minutes": 120, "title": ..., "location": ..., "note": ...}
                 või terve päeva sündmus: {"date": "YYYY-MM-DD", "title": ...}
"""
import hashlib
import json
import pathlib
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "spordikalender.ics"
CACHE = ROOT / "cache"
UA = "Mozilla/5.0 (spordikalender; +https://github.com/andri-tallo/spordikalender)"


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line: str) -> list[str]:
    """RFC 5545 reamurdmine 75 oktetti kaupa."""
    out, b = [], line.encode()
    while len(b) > 75:
        cut = 75 if not out else 74
        while (b[cut] & 0xC0) == 0x80:  # ära lõika UTF-8 märki pooleks
            cut -= 1
        out.append(b[:cut].decode())
        b = b[cut:]
    out.append(b.decode())
    return [out[0]] + [" " + x for x in out[1:]]


def unfold(text: str) -> list[str]:
    return re.sub(r"\r?\n[ \t]", "", text).splitlines()


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def feed_events(feed: dict) -> tuple[list[list[str]], list[list[str]]]:
    cache = CACHE / f"{feed['id']}.ics"
    try:
        text = fetch(feed["url"])
        if "BEGIN:VCALENDAR" not in text:
            raise ValueError("vastus pole ICS")
        cache.write_text(text, encoding="utf-8")
        print(f"[ok] {feed['id']}: laetud", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        if not cache.exists():
            print(f"[viga] {feed['id']}: {e}; vahemälu puudub, jätan vahele", file=sys.stderr)
            return [], []
        print(f"[hoiatus] {feed['id']}: {e}; kasutan vahemälu", file=sys.stderr)
        text = cache.read_text(encoding="utf-8")

    events, tzs, cur, kind = [], [], None, None
    for ln in unfold(text):
        if ln in ("BEGIN:VEVENT", "BEGIN:VTIMEZONE") and cur is None:
            cur, kind = [ln], ln[6:]
            continue
        if cur is None:
            continue
        if kind == "VEVENT":
            if ln.startswith("SUMMARY"):
                k, v = ln.split(":", 1)
                ln = f"{k}:{feed['prefix']}{v}"
            elif ln.startswith("UID"):
                k, v = ln.split(":", 1)
                ln = f"{k}:{feed['id']}-{v}"
        cur.append(ln)
        if ln == f"END:{kind}":
            (events if kind == "VEVENT" else tzs).append(cur)
            cur = None
    return events, tzs


def local_events(path: pathlib.Path, stamp: str) -> list[list[str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for e in data["events"]:
        uid = hashlib.sha1(f"{path.stem}|{e.get('start') or e.get('date')}|{e['title']}".encode()).hexdigest()[:16]
        ev = ["BEGIN:VEVENT", f"UID:{path.stem}-{uid}@spordikalender", f"DTSTAMP:{stamp}"]
        if "date" in e:
            d = datetime.strptime(e["date"], "%Y-%m-%d")
            ev += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
        else:
            s = datetime.strptime(e["start"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(e["tz"])).astimezone(timezone.utc)
            en = s + timedelta(minutes=e.get("minutes", 120))
            ev += [f"DTSTART:{s:%Y%m%dT%H%M%SZ}", f"DTEND:{en:%Y%m%dT%H%M%SZ}"]
        ev.append(f"SUMMARY:{esc(e['title'])}")
        if e.get("location"):
            ev.append(f"LOCATION:{esc(e['location'])}")
        desc = "\n".join(x for x in (e.get("note"), f"Allikas: {data.get('source', '')}") if x)
        ev.append(f"DESCRIPTION:{esc(desc)}")
        ev.append("END:VEVENT")
        out.append(ev)
    return out


def main() -> None:
    CACHE.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    events, tzs, seen_tz = [], [], set()

    for feed in json.loads((ROOT / "feeds.json").read_text(encoding="utf-8"))["feeds"]:
        ev, tz = feed_events(feed)
        events += ev
        for t in tz:
            tzid = next((x for x in t if x.startswith("TZID")), "")
            if tzid not in seen_tz:
                seen_tz.add(tzid)
                tzs.append(t)

    for p in sorted((ROOT / "data").glob("*.json")):
        events += local_events(p, stamp)

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//andri-tallo//spordikalender//ET",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Spordikalender",
             "X-WR-TIMEZONE:Europe/Tallinn", "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
             "X-PUBLISHED-TTL:PT6H"]
    for block in tzs + events:
        lines += block
    lines.append("END:VCALENDAR")

    body = "\r\n".join(f for ln in lines for f in fold(ln)) + "\r\n"
    # DTSTAMP muutub igal käivitusel; võrdle ilma selleta, et vältida tühje commit'e
    strip = lambda s: re.sub(r"DTSTAMP:\d{8}T\d{6}Z", "", s)
    if OUT.exists() and strip(OUT.read_text(encoding="utf-8")) == strip(body):
        print("muudatusi pole", file=sys.stderr)
        return
    OUT.write_text(body, encoding="utf-8", newline="")
    print(f"kirjutatud {OUT.name}: {len(events)} sündmust", file=sys.stderr)


if __name__ == "__main__":
    main()
