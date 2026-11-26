#!/usr/bin/env python3
"""Paneb kokku spordikalender.ics.

Allikad (sources.json):
  ics          – välised ICS-vood (FotMob).
  fiba         – FIBA mängulehed (fiba.basketball/en/games/<id>), ametlik aeg ja koht.
  dataproject  – võrkpalli võistluste lehed (Balti liiga, EVF), filtreeritud meeskonna järgi.
  Kui allika laadimine ebaõnnestub, kasutatakse cache/ kausta viimast head koopiat.
Lisaks:
  data/*.json  – käsitsi hallatavad sündmused.
                 {"start": "YYYY-MM-DD HH:MM", "tz": "Europe/Tallinn", "minutes": 120, "title": ..., "location": ..., "note": ...}
                 või terve päeva sündmus: {"date": "YYYY-MM-DD", "title": ...}
"""
import hashlib
import html
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


def write_if_changed(path: pathlib.Path, text: str) -> None:
    """Kirjuta ainult sisulise muutuse korral (DTSTAMP-i ei arvestata), et vältida tühje commit'e."""
    norm = lambda x: re.sub(r"DTSTAMP[:;][^\r\n\"]*", "", x)
    if path.exists() and norm(path.read_text(encoding="utf-8")) == norm(text):
        return
    path.write_text(text, encoding="utf-8", newline="")


def try_fetch(key: str, url: str, check: str) -> str | None:
    try:
        text = fetch(url)
        if check not in text:
            raise ValueError("oodatud sisu puudub")
        return text
    except Exception as e:  # noqa: BLE001
        print(f"[viga] {key}: {e}", file=sys.stderr)
        return None


def with_cache(key: str, blocks: list[list[str]] | None) -> list[list[str]]:
    """Salvestab õnnestunud tulemuse cache/<key>.json; ebaõnnestumisel tagastab viimase hea."""
    path = CACHE / f"{key}.json"
    if blocks is not None:
        write_if_changed(path, json.dumps(blocks, ensure_ascii=False, indent=0))
        return blocks
    if path.exists():
        print(f"[hoiatus] {key}: kasutan vahemälu", file=sys.stderr)
        return json.loads(path.read_text(encoding="utf-8"))
    return []


ET = {"Estonia": "Eesti", "France": "Prantsusmaa", "Finland": "Soome", "Hungary": "Ungari", "Sweden": "Rootsi",
      "Slovenia": "Sloveenia", "Latvia": "Läti", "Lithuania": "Leedu", "Germany": "Saksamaa", "Spain": "Hispaania",
      "Italy": "Itaalia", "Poland": "Poola", "Czechia": "Tšehhi", "Croatia": "Horvaatia", "Serbia": "Serbia",
      "Greece": "Kreeka", "Türkiye": "Türgi", "Israel": "Iisrael", "Belgium": "Belgia", "Netherlands": "Holland",
      "Georgia": "Gruusia", "Ukraine": "Ukraina", "Iceland": "Island", "Portugal": "Portugal", "Denmark": "Taani",
      "Montenegro": "Montenegro", "Bosnia and Herzegovina": "Bosnia ja Hertsegoviina", "Great Britain": "Suurbritannia"}


def event_block(uid, stamp, title, start_utc=None, minutes=120, day=None, location=None, desc=None):
    ev = ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}"]
    if day:
        ev += [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}"]
    else:
        ev += [f"DTSTART:{start_utc:%Y%m%dT%H%M%SZ}", f"DTEND:{start_utc + timedelta(minutes=minutes):%Y%m%dT%H%M%SZ}"]
    ev.append(f"SUMMARY:{esc(title)}")
    if location:
        ev.append(f"LOCATION:{esc(location)}")
    if desc:
        ev.append(f"DESCRIPTION:{esc(desc)}")
    ev.append("END:VEVENT")
    return ev


def fiba_events(cfg: dict, stamp: str) -> list[list[str]]:
    out = []
    for g in cfg["games"]:
        url = f"https://www.fiba.basketball/en/games/{g['id']}"
        text = try_fetch(f"fiba-{g['id']}", url, "gameDateTime")
        if not text:
            out += with_cache(f"fiba-{g['id']}", None)
            continue
        t = text.replace('\\"', '"')
        m = re.search(r'"gameDateTime":"([^"]+)","gameDateTimeUTC":"([^"]+)","hasTimeGameDateTime":(true|false)', t)
        if not m:
            print(f"[viga] fiba {g['id']}: aega ei leitud", file=sys.stderr)
            continue
        pre = t[: m.start()]
        teams = list(re.finditer(r'"teamA":\{[^{}]*?"officialName":"([^"]+)"[^{}]*\},"teamB":\{[^{}]*?"officialName":"([^"]+)"', pre))
        a, b = (teams[-1].group(1), teams[-1].group(2)) if teams else ("?", "?")
        venue = re.search(r'"venueName":"([^"]+)"', t[m.start() - 300: m.start()])
        city = re.search(r'"hostCity":"([^"]+)"', t[m.start() - 400: m.start()])
        score = re.search(r'"teamAScore":(\d+),"teamBScore":(\d+)', t[m.start() - 600: m.start()])
        title = f"🏀 {ET.get(a, a)} – {ET.get(b, b)} ({g.get('competition', 'korvpall')})"
        loc = ", ".join(x.group(1) for x in (venue, city) if x) or None
        desc = [f"FIBA: {url}"]
        if score and int(score.group(1)) + int(score.group(2)) > 0:
            desc.insert(0, f"Tulemus {score.group(1)}:{score.group(2)}")
        uid = f"fiba-{g['id']}@spordikalender"
        if m.group(3) == "true":
            s = datetime.strptime(m.group(2), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
            blk = event_block(uid, stamp, title, start_utc=s, minutes=120, location=loc, desc="\n".join(desc))
        else:
            d = datetime.strptime(m.group(1)[:10], "%Y-%m-%d")
            desc.insert(0, "Kellaaeg täpsustamisel")
            blk = event_block(uid, stamp, title, day=d, location=loc, desc="\n".join(desc))
        out += with_cache(f"fiba-{g['id']}", [blk])
        print(f"[ok] fiba {g['id']}: {title} {m.group(2) if m.group(3) == 'true' else m.group(1)[:10]}", file=sys.stderr)
    return out


DP_FIELDS = ("LB_DataOra", "LB_Palasport", "Label2", "Label4", "Label6", "Label7",
             "LBL_HomeTeamName", "LBL_GuestTeamName", "LB_SetCasa", "LB_SetOspiti")


def dataproject_events(cfg: dict, stamp: str) -> list[list[str]]:
    url = f"https://{cfg['host']}/CompetitionMatches.aspx?ID={cfg['competition']}"
    text = try_fetch(f"dp-{cfg['id']}", url, "CompetitionMatches")
    if not text:
        return with_cache(f"dp-{cfg['id']}", None)
    rows: dict[str, dict] = {}
    for m in re.finditer(r'id="(ctl00_[^"]*?RADLIST_Matches_ctrl\d+)_(' + "|".join(DP_FIELDS) + r')"[^>]*>([^<]*)<', text):
        rows.setdefault(m.group(1), {}).setdefault(m.group(2), html.unescape(m.group(3)).strip())
    out = []
    for key, r in rows.items():
        home = r.get("Label6") or r.get("Label2") or r.get("LBL_HomeTeamName", "")
        away = r.get("Label7") or r.get("Label4") or r.get("LBL_GuestTeamName", "")
        if cfg["team"] not in (home, away):
            continue
        try:
            local = datetime.strptime(r["LB_DataOra"], "%d/%m/%Y - %H:%M")
        except (KeyError, ValueError):
            continue
        s = local.replace(tzinfo=ZoneInfo(cfg.get("tz", "Europe/Tallinn"))).astimezone(timezone.utc)
        res = f"{r.get('LB_SetCasa', '')}:{r.get('LB_SetOspiti', '')}"
        desc = [f"Tulemus {res}"] if res.strip(":") and res != "0:0" else []
        desc.append(f"Allikas: {url}")
        mid = hashlib.sha1(f"{cfg['id']}|{key}|{home}|{away}|{local:%Y%m%d}".encode()).hexdigest()[:16]
        out.append(event_block(f"dp-{cfg['id']}-{mid}@spordikalender", stamp,
                               f"🏐 {home} – {away} ({cfg['label']})", start_utc=s, minutes=120,
                               location=r.get("LB_Palasport") or None, desc="\n".join(desc)))
    print(f"[ok] dataproject {cfg['id']}: {len(out)} mängu ({cfg['team']})", file=sys.stderr)
    return with_cache(f"dp-{cfg['id']}", out)


def feed_events(feed: dict) -> tuple[list[list[str]], list[list[str]]]:
    cache = CACHE / f"{feed['id']}.ics"
    try:
        text = fetch(feed["url"])
        if "BEGIN:VCALENDAR" not in text:
            raise ValueError("vastus pole ICS")
        write_if_changed(cache, text)
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

    src = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    for feed in src.get("ics", []):
        ev, tz = feed_events(feed)
        events += ev
        for t in tz:
            tzid = next((x for x in t if x.startswith("TZID")), "")
            if tzid not in seen_tz:
                seen_tz.add(tzid)
                tzs.append(t)

    if "fiba" in src:
        events += fiba_events(src["fiba"], stamp)
    for dp in src.get("dataproject", []):
        events += dataproject_events(dp, stamp)

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
