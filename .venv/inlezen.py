"""Inlezen en controleren van het deelnemersbestand (Excel).

Verwachte kolommen (één rij per huis):
    adres, naam, aantalpersonen, voorgerecht, hoofdgerecht, nagerecht,
    kids, kids_mee, maxaantaleters, dieetwensen

- voorgerecht/hoofdgerecht/nagerecht: J of N (wil deze gang koken)
- kids:     J of N (kinderen welkom als bezoek)
- kids_mee: J of N (neemt zelf kinderen mee)
- maxaantaleters: maximaal aantal bezoekers (personen), hoogstens MAX_BEZOEKERS
- dieetwensen: vrije tekst, mag leeg zijn

Alle fouten in het bestand worden in één keer gemeld, met het rijnummer
zoals je dat in Excel ziet.
"""

import csv
import math
from pathlib import Path

import pandas as pd

from huis import GANGEN, Huis

STANDAARD_BESTAND = "roulette2026najaar.xlsx"
STANDAARD_BLAD = "Blad1"
MAX_BEZOEKERS = 8

VERPLICHTE_KOLOMMEN = (
    "adres", "naam", "aantalpersonen",
    "voorgerecht", "hoofdgerecht", "nagerecht",
    "kids", "kids_mee", "maxaantaleters",
)
OPTIONELE_KOLOMMEN = ("dieetwensen",)


class InleesFout(Exception):
    """Het deelnemersbestand bevat een of meer fouten."""


def _is_leeg(waarde) -> bool:
    return waarde is None or (isinstance(waarde, float) and math.isnan(waarde)) or str(waarde).strip() == ""


def _tekst(waarde) -> str:
    return "" if _is_leeg(waarde) else str(waarde).strip()


def _ja_nee(waarde, kolom: str, fouten: list) -> bool:
    tekst = _tekst(waarde).upper()
    if tekst in ("J", "JA"):
        return True
    if tekst in ("N", "NEE"):
        return False
    fouten.append(f"kolom '{kolom}' moet J of N zijn, maar is '{_tekst(waarde)}'")
    return False


def _geheel_getal(waarde, kolom: str, fouten: list, minimum: int = 1) -> int:
    try:
        getal = float(waarde)
        if getal != int(getal):
            raise ValueError
        getal = int(getal)
    except (TypeError, ValueError):
        fouten.append(f"kolom '{kolom}' moet een geheel getal zijn, maar is '{_tekst(waarde)}'")
        return 0
    if getal < minimum:
        fouten.append(f"kolom '{kolom}' moet minimaal {minimum} zijn, maar is {getal}")
    return getal


def _rij_naar_huis(rij: dict, fouten: list) -> Huis:
    adres = _tekst(rij["adres"])
    if not adres:
        fouten.append("adres is leeg")
    naam = _tekst(rij["naam"])
    if not naam:
        fouten.append("naam is leeg")

    aantal_personen = _geheel_getal(rij["aantalpersonen"], "aantalpersonen", fouten)
    max_eters = _geheel_getal(rij["maxaantaleters"], "maxaantaleters", fouten)
    if max_eters > MAX_BEZOEKERS:
        fouten.append(f"maxaantaleters is {max_eters}, maar het maximum is {MAX_BEZOEKERS}")

    # Een lege gang-kolom telt als "N" (wil deze gang liever niet koken).
    lege_gangen = [g for g in GANGEN if _is_leeg(rij[g])]
    if lege_gangen:
        print(f"[WAARSCHUWING] {adres}: kolom {', '.join(lege_gangen)} is leeg, telt als N")
    voorkeur = frozenset(g for g in GANGEN
                         if g not in lege_gangen and _ja_nee(rij[g], g, fouten))
    if not voorkeur:
        # Niemand wil "geen enkele gang" koken; we lezen dit als "geen voorkeur".
        voorkeur = frozenset(GANGEN)

    return Huis(
        adres=adres,
        naam=naam,
        aantal_personen=aantal_personen,
        max_eters=max_eters,
        voorkeur_gangen=voorkeur,
        kids_welkom=_ja_nee(rij["kids"], "kids", fouten),
        kids_mee=_ja_nee(rij["kids_mee"], "kids_mee", fouten),
        dieetwensen=_tekst(rij.get("dieetwensen")),
    )


def lees_deelnemers(bestand=STANDAARD_BESTAND, blad=STANDAARD_BLAD) -> list:
    """Lees het Excel-bestand en geef een lijst Huis-objecten terug.

    Gooit InleesFout met een overzicht van alle gevonden problemen.
    """
    pad = Path(bestand)
    if not pad.exists():
        raise InleesFout(f"Bestand '{pad}' bestaat niet.")

    try:
        df = pd.read_excel(pad, sheet_name=blad)
    except ValueError as e:  # o.a. als het werkblad niet bestaat
        raise InleesFout(f"Kan werkblad '{blad}' in '{pad}' niet lezen: {e}") from e

    # Kolomnamen ongevoelig maken voor hoofdletters en spaties.
    df.columns = [str(k).strip().lower() for k in df.columns]
    ontbrekend = [k for k in VERPLICHTE_KOLOMMEN if k not in df.columns]
    if ontbrekend:
        raise InleesFout(f"Kolommen ontbreken in '{pad}': {', '.join(ontbrekend)}")

    # Helemaal lege rijen (bijv. onderaan het blad) overslaan.
    df = df.dropna(how="all")

    huizen, alle_fouten = [], []
    for index, rij in df.iterrows():
        excel_rij = index + 2  # +1 voor de kopregel, +1 omdat Excel bij 1 begint
        fouten = []
        huis = _rij_naar_huis(rij.to_dict(), fouten)
        alle_fouten += [f"rij {excel_rij} ({huis.adres or '?'}): {f}" for f in fouten]
        huizen.append(huis)

    # Het adres wordt in het hele programma als sleutel gebruikt: moet uniek zijn.
    gezien = set()
    for huis in huizen:
        if huis.adres and huis.adres in gezien:
            alle_fouten.append(f"adres '{huis.adres}' komt meer dan één keer voor")
        gezien.add(huis.adres)

    if alle_fouten:
        raise InleesFout("Fouten in het deelnemersbestand:\n  - " + "\n  - ".join(alle_fouten))

    return huizen


def lees_vorige_keer(bestand) -> list:
    """Lees wie er de vorige keer bij wie at.

    Formaat (csv, één regel per kookhuis):  koker_adres, naam, gang, gast_adres, gast_adres, ...
    Geeft een lijst (koker_adres, gast_adres)-paren. Bestaat het bestand niet: lege lijst.
    """
    pad = Path(bestand)
    if not pad.exists():
        print(f"[INFO] Geen bestand '{pad}' met de vorige editie gevonden; die wordt niet meegenomen.")
        return []
    paren = []
    with open(pad, newline="", encoding="utf-8") as f:
        for regel in csv.reader(f):
            regel = [veld.strip() for veld in regel]
            if len(regel) >= 4 and regel[0]:
                paren += [(regel[0], gast) for gast in regel[3:] if gast]
    print(f"[INFO] {len(paren)} koker-gast-combinaties van de vorige keer gelezen uit '{pad}'.")
    return paren


def toon_samenvatting(huizen: list) -> None:
    """Print een korte samenvatting van de ingelezen deelnemers."""
    print(f"[INFO] {len(huizen)} huizen, {sum(h.aantal_personen for h in huizen)} deelnemers ingelezen")
    for gang in GANGEN:
        aantal = sum(gang in h.voorkeur_gangen for h in huizen)
        print(f"[INFO]   wil {gang} koken: {aantal}")
    print(f"[INFO]   gezinnen met kinderen: {sum(h.kids_mee for h in huizen)}, "
          f"kinderen niet welkom bij: {sum(not h.kids_welkom for h in huizen)}")


if __name__ == "__main__":
    # Los te draaien om alleen het bestand te controleren:  python inlezen.py [bestand]
    import sys

    try:
        huizen = lees_deelnemers(*sys.argv[1:2])
    except InleesFout as fout:
        sys.exit(str(fout))
    toon_samenvatting(huizen)
    for h in huizen:
        print(f"  {h.adres:<20} {h.naam:<28} {h.aantal_personen}p  max {h.max_eters}  "
              f"voorkeur {h.voorkeur_code}  kids welkom {'J' if h.kids_welkom else 'N'}  "
              f"kids mee {'J' if h.kids_mee else 'N'}")
