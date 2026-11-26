# Spordikalender

Üks tellitav kalender, kus on kõik jälgitavad spordiülekanded.

**Tellimise aadress:**

```
webcal://raw.githubusercontent.com/andri-tallo/spordikalender/main/spordikalender.ics
```

- **Mac:** Calendar → File → New Calendar Subscription → kleebi aadress → Auto-refresh: Every hour.
- **iPhone:** Settings → Apps → Calendar → Calendar Accounts → Add Account → Other → Add Subscribed Calendar.

## Sisu

| Mis | Kust | Uueneb |
|---|---|---|
| FC Barcelona (kõik sarjad) | FotMob ICS (`feeds.json`) | automaatselt |
| Eesti jalgpallikoondis | FotMob ICS (`feeds.json`) | automaatselt |
| Laskesuusatamise MK 2026/27 + Otepää MM | `data/laskesuusatamine.json` | iganädalane kontroll |
| Eesti korvpallikoondis | `data/korvpall.json` | iganädalane kontroll |
| Barrus Võru VK, Eesti võrkpallikoondis | `data/vorkpall.json` | iganädalane kontroll |

GitHub Actions paneb kalendri kokku iga 6 tunni järel ja iga kord, kui andmefailid muutuvad (`build.py`).

## Uue meeskonna lisamine

- Kui allikal on ICS-voog, lisa see faili `feeds.json`.
- Kui pole, tee uus fail `data/<nimi>.json` samas vormingus nagu teised.
  Sündmusel on kas `start` + `tz` (kohalik aeg ja ajavöönd) või `date` (terve päeva sündmus, kui kellaaeg pole teada).
