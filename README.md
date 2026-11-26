# Spordikalender

Üks tellitav kalender, kus on kõik jälgitavad spordiülekanded.

**Tellimise aadress:**

```
webcal://raw.githubusercontent.com/andri-tallo/spordikalender/main/spordikalender.ics
```

- **Mac:** Calendar → File → New Calendar Subscription → kleebi aadress → Auto-refresh: Every hour.
- **iPhone:** Settings → Apps → Calendar → Calendar Accounts → Add Account → Other → Add Subscribed Calendar.

## Sisu

| Mis | Allikas | Uueneb |
|---|---|---|
| FC Barcelona (kõik sarjad) | FotMob ICS | automaatselt |
| Eesti jalgpallikoondis | FotMob ICS | automaatselt |
| Eesti korvpallikoondis | FIBA mängulehed (`sources.json` → `fiba`) | ajad automaatselt; uued mängu-ID-d tuleb lisada |
| Barrus Võru VK: Balti liiga, Aadu Luukase karikas, Eesti meistrivõistlused | Dataproject (`sources.json` → `dataproject`) | automaatselt; uue hooaja võistluse ID-d tuleb lisada |
| Laskesuusatamise MK 2026/27 + Otepää MM | `data/laskesuusatamine.json` | käsitsi |

GitHub Actions paneb kalendri kokku iga 6 tunni järel (`build.py`). Kui mõni allikas ajutiselt ei vasta, kasutatakse `cache/` kausta viimast head tulemust.

## Uue meeskonna lisamine

- Kui allikal on ICS-voog, lisa see faili `sources.json` (`ics`).
- Kui pole, tee uus fail `data/<nimi>.json` samas vormingus nagu teised.
  Sündmusel on kas `start` + `tz` (kohalik aeg ja ajavöönd) või `date` (terve päeva sündmus, kui kellaaeg pole teada).
