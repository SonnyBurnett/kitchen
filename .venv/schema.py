"""Het maken (en controleren) van een Kitchen Roulette-schema.

Regels:
  1. Ieder huis kookt precies één gang, en die gang past bij zijn voorkeur.
  2. Bij ieder kookhuis komen minimaal 1 en maximaal MAX_GASTEN andere huizen.
  3. Het aantal bezoekers (personen) is niet meer dan wat het kookhuis opgeeft.
  4. Huizen die kinderen meenemen gaan niet naar een huis waar kinderen niet welkom zijn.
  5. Twee huizen zitten hooguit één keer samen aan tafel, over alle drie de gangen.
  6. (Optioneel) Een kookhuis krijgt geen gast waarvoor het vorige keer ook kookte.
  7. Ieder gezin met kinderen zit minstens één keer aan tafel met een ander gezin
     met kinderen (als gast of als gastheer). Vervalt als er maar één zo'n gezin is.

Werkwijze:
  - Eerst krijgt ieder huis een gang (zo gelijk mogelijk verdeeld, met voorkeuren).
  - Daarna worden gasten over de kookhuizen verdeeld met *backtracking*: kan een
    gast nergens meer terecht, dan wordt een eerdere keuze teruggedraaid en wordt
    iets anders geprobeerd. We kiezen steeds eerst de gast met de minste
    mogelijkheden; dat maakt het zoeken veel sneller.
  - Lukt het met deze gangverdeling niet snel genoeg, dan proberen we een andere.

controleer_schema() controleert een uitkomst los van de zoekcode.
"""

import random
import time
from itertools import combinations, permutations

from huis import GANGEN

MAX_GASTEN = 3  # maximaal aantal bezoekende huizen per kookhuis


class GeenSchemaGevonden(Exception):
    """Er is (binnen het aantal pogingen) geen geldig schema gevonden."""


def normaliseer_adres(adres: str) -> str:
    """'Warder 174 A' en 'warder 174a' zijn hetzelfde adres."""
    return "".join(str(adres).split()).lower()


# ----------------------------------------------------------------------------
# Stap 1: gangen toekennen
# ----------------------------------------------------------------------------

def _gewenste_aantallen(aantal_huizen: int, rng: random.Random) -> dict:
    """Verdeel het aantal kookhuizen zo gelijk mogelijk over de gangen.

    De gang(en) die een kookhuis extra krijgen, worden willekeurig gekozen.
    """
    basis, rest = divmod(aantal_huizen, 3)
    extra = set(rng.sample(GANGEN, rest))
    return {g: basis + (1 if g in extra else 0) for g in GANGEN}


def ken_gangen_toe(huizen: list, rng: random.Random):
    """Geef ieder huis een gang die bij zijn voorkeur past.

    Geeft {index: gang} terug, of None als het met deze aantallen niet kan.
    """
    aantallen = _gewenste_aantallen(len(huizen), rng)
    # Huizen met de minste keuze eerst, verder in willekeurige volgorde.
    volgorde = list(range(len(huizen)))
    rng.shuffle(volgorde)
    volgorde.sort(key=lambda i: len(huizen[i].voorkeur_gangen))

    toewijzing = {}

    def zoek(pos: int) -> bool:
        if pos == len(volgorde):
            return True
        i = volgorde[pos]
        opties = [g for g in huizen[i].voorkeur_gangen if aantallen[g] > 0]
        rng.shuffle(opties)
        for gang in opties:
            aantallen[gang] -= 1
            toewijzing[i] = gang
            if zoek(pos + 1):
                return True
            aantallen[gang] += 1
            del toewijzing[i]
        return False

    return toewijzing if zoek(0) else None


def kan_gangen_verdelen(huizen: list) -> bool:
    """Is er überhaupt een gelijke verdeling die bij de voorkeuren past?"""
    basis, rest = divmod(len(huizen), 3)
    for extra in set(permutations([1] * rest + [0] * (3 - rest))):
        aantallen = {g: basis + e for g, e in zip(GANGEN, extra)}
        # Simpele check per combinatie van gangen (stelling van Hall).
        for k in (1, 2, 3):
            for gangen in combinations(GANGEN, k):
                kunnen = sum(1 for h in huizen if h.voorkeur_gangen & set(gangen))
                moeten = len(huizen) - sum(aantallen[g] for g in GANGEN if g not in gangen)
                if kunnen < moeten:
                    break
            else:
                continue
            break
        else:
            return True
    return False


# ----------------------------------------------------------------------------
# Stap 2: gasten over de kookhuizen verdelen
# ----------------------------------------------------------------------------

class _Zoeker:
    """Verdeelt bij een vaste gangverdeling de gasten over de kookhuizen."""

    def __init__(self, huizen, gang_van, verboden, rng, max_stappen):
        self.huizen = huizen
        self.n = len(huizen)
        self.gang_van = gang_van
        self.verboden = verboden          # set van (koker_index, gast_index)
        self.rng = rng
        self.max_stappen = max_stappen
        self.stappen = 0

        self.kokers = {g: [i for i in range(self.n) if gang_van[i] == g] for g in GANGEN}
        self.gasten_bij = {i: [] for i in range(self.n)}   # koker -> lijst gasten
        self.personen_bij = [0] * self.n                    # koker -> aantal bezoekers
        self.ontmoet = [[0] * self.n for _ in range(self.n)]
        self.tafel = {}                                     # (gang, gast) -> koker
        self.open = {(g, i) for g in GANGEN for i in range(self.n) if gang_van[i] != g}
        # Regel 7: gezinnen met kinderen moeten een ander gezin met kinderen treffen.
        self.kids = {i for i in range(self.n) if huizen[i].kids_mee}
        self.kids_regel = len(self.kids) >= 2

    # -- hulpfuncties --------------------------------------------------------

    def _past(self, gang, gast, koker) -> bool:
        h_gast, h_koker = self.huizen[gast], self.huizen[koker]
        if len(self.gasten_bij[koker]) >= MAX_GASTEN:
            return False
        if self.personen_bij[koker] + h_gast.aantal_personen > h_koker.max_eters:
            return False
        if h_gast.kids_mee and not h_koker.kids_welkom:
            return False
        if (koker, gast) in self.verboden:
            return False
        if self.ontmoet[gast][koker]:
            return False
        return not any(self.ontmoet[gast][andere] for andere in self.gasten_bij[koker])

    def _tafel_heeft_kids(self, koker) -> bool:
        return koker in self.kids or any(g in self.kids for g in self.gasten_bij[koker])

    def _kids_tevreden(self, i) -> bool:
        """Heeft gezin i al een ander gezin met kinderen ontmoet?"""
        return any(self.ontmoet[i][j] for j in self.kids if j != i)

    def _kids_nog_haalbaar(self, opties_per_open) -> bool:
        """Kan ieder gezin met kinderen nog een ander gezin met kinderen treffen?

        Ruime (optimistische) controle: als dit False geeft, kan het zeker niet meer.
        """
        if not self.kids_regel:
            return True
        # Tafels waar nog een gezin met kinderen bij kan komen: {(gang, koker)}.
        kids_kan_nog_naar = {(gang, k) for (gang, j), opties in opties_per_open.items()
                             if j in self.kids for k in opties}
        for i in self.kids:
            if self._kids_tevreden(i):
                continue
            # a) i is nog niet ingedeeld voor een gang en kan naar een tafel
            #    met kinderen, of naar een tafel waar nog kinderen bij kunnen komen.
            if any(gast == i and any(self._tafel_heeft_kids(k) or (gang, k) in kids_kan_nog_naar
                                     for k in opties)
                   for (gang, gast), opties in opties_per_open.items()):
                continue
            # b) Aan een tafel waar i al zit (als kok of gast) kan nog een gezin met kinderen komen.
            tafels_van_i = [(self.gang_van[i], i)] + [(g, k) for (g, gast), k in self.tafel.items()
                                                     if gast == i]
            if any(t in kids_kan_nog_naar for t in tafels_van_i):
                continue
            return False
        return True

    def _opties(self, gang, gast) -> list:
        return [k for k in self.kokers[gang] if self._past(gang, gast, k)]

    def _zet(self, gang, gast, koker, delta):
        """Plaats (delta=+1) of verwijder (delta=-1) een gast aan een tafel."""
        aan_tafel = [koker] + self.gasten_bij[koker]
        if delta < 0:
            self.gasten_bij[koker].remove(gast)
            aan_tafel = [koker] + self.gasten_bij[koker]
        for ander in aan_tafel:
            self.ontmoet[gast][ander] += delta
            self.ontmoet[ander][gast] += delta
        if delta > 0:
            self.gasten_bij[koker].append(gast)
            self.tafel[(gang, gast)] = koker
            self.open.discard((gang, gast))
        else:
            del self.tafel[(gang, gast)]
            self.open.add((gang, gast))
        self.personen_bij[koker] += delta * self.huizen[gast].aantal_personen

    def _lege_tafels_nog_te_vullen(self, opties_per_open) -> bool:
        """Elke koker zonder gasten moet nog minstens één mogelijke gast hebben."""
        for gang in GANGEN:
            open_in_gang = [(gang, g) for (gg, g) in self.open if gg == gang]
            leeg = [k for k in self.kokers[gang] if not self.gasten_bij[k]]
            if len(leeg) > len(open_in_gang):
                return False
            # Passen de nog open gasten (in personen en in huizen) nog bij de kokers?
            vrije_plekken = sum(MAX_GASTEN - len(self.gasten_bij[k]) for k in self.kokers[gang])
            vrije_stoelen = sum(self.huizen[k].max_eters - self.personen_bij[k] for k in self.kokers[gang])
            if (len(open_in_gang) > vrije_plekken or
                    sum(self.huizen[g].aantal_personen for _, g in open_in_gang) > vrije_stoelen):
                return False
            for koker in leeg:
                if not any(koker in opties_per_open[p] for p in open_in_gang):
                    return False
        return True

    # -- het zoeken ------------------------------------------------------------

    def zoek(self) -> bool:
        if not self.open:
            return (all(self.gasten_bij[k] for g in GANGEN for k in self.kokers[g]) and
                    (not self.kids_regel or all(self._kids_tevreden(i) for i in self.kids)))
        self.stappen += 1
        if self.stappen > self.max_stappen:
            return False

        opties_per_open = {p: self._opties(*p) for p in self.open}
        if not self._lege_tafels_nog_te_vullen(opties_per_open):
            return False
        if not self._kids_nog_haalbaar(opties_per_open):
            return False

        # De gast met de minste mogelijkheden eerst (bij gelijkspel: willekeurig).
        gang, gast = min(opties_per_open, key=lambda p: (len(opties_per_open[p]), self.rng.random()))
        opties = opties_per_open[(gang, gast)]
        # Een gezin met kinderen dat nog geen ander gezin met kinderen trof, gaat bij
        # voorkeur naar een tafel met kinderen. Verder liefst naar een tafel met weinig
        # gasten, zodat de tafels gelijkmatig vullen.
        zoekt_kids = self.kids_regel and gast in self.kids and not self._kids_tevreden(gast)
        opties.sort(key=lambda k: (not (zoekt_kids and self._tafel_heeft_kids(k)),
                                   len(self.gasten_bij[k]), self.rng.random()))

        for koker in opties:
            self._zet(gang, gast, koker, +1)
            if self.zoek():
                return True
            self._zet(gang, gast, koker, -1)
        return False


# ----------------------------------------------------------------------------
# Alles samen
# ----------------------------------------------------------------------------

def _verboden_paren(huizen, vorige_keer) -> set:
    """Zet {(koker_adres, gast_adres)} van de vorige keer om naar indexen."""
    index = {normaliseer_adres(h.adres): i for i, h in enumerate(huizen)}
    paren = set()
    for koker, gast in vorige_keer or ():
        k, g = index.get(normaliseer_adres(koker)), index.get(normaliseer_adres(gast))
        if k is not None and g is not None:
            paren.add((k, g))
    return paren


def _schrijf_uitkomst(huizen, gang_van, zoeker):
    for i, huis in enumerate(huizen):
        huis.gang = gang_van[i]
        for gang in GANGEN:
            koker = i if gang_van[i] == gang else zoeker.tafel[(gang, i)]
            setattr(huis, gang, huizen[koker].adres)
        gasten = zoeker.gasten_bij[i]
        huis.aantal_huizen = len(gasten)
        huis.aantal_eters = sum(huizen[g].aantal_personen for g in gasten)
        huis.lijst_eters = sorted(huizen[j].adres for j in range(len(huizen))
                                  if zoeker.ontmoet[i][j])


def maak_schema(huizen: list, vorige_keer=None, seed=None,
                max_seconden: float = 60, max_stappen: int = 5000) -> list:
    """Maak een geldig schema en vul de Huis-objecten met de uitkomst.

    vorige_keer:  lijst (koker_adres, gast_adres)-paren die niet mogen terugkomen.
    seed:         geef een getal op om precies hetzelfde schema opnieuw te krijgen.
    max_seconden: zo lang wordt er maximaal gezocht.
    """
    if len(huizen) < 4:
        raise GeenSchemaGevonden("Er zijn minimaal 4 huizen nodig.")
    if not kan_gangen_verdelen(huizen):
        raise GeenSchemaGevonden(
            "De gangvoorkeuren laten geen gelijke verdeling over de drie gangen toe. "
            "Vraag een paar huizen of ze ook een andere gang willen koken.")

    if sum(h.kids_mee for h in huizen) == 1:
        print("[WAARSCHUWING] Er is maar één gezin met kinderen; de regel 'kinderen ontmoeten "
              "elkaar' kan niet en wordt overgeslagen.")

    rng = random.Random(seed)
    verboden = _verboden_paren(huizen, vorige_keer)
    start = volgende_melding = time.monotonic()
    poging = 0

    while time.monotonic() - start < max_seconden:
        poging += 1
        gang_van = ken_gangen_toe(huizen, rng)
        if gang_van is None:
            continue  # deze verdeling van de 'extra' kookhuizen past niet bij de voorkeuren
        zoeker = _Zoeker(huizen, gang_van, verboden, rng, max_stappen)
        if zoeker.zoek():
            _schrijf_uitkomst(huizen, gang_van, zoeker)
            print(f"[INFO] Schema gevonden in poging {poging} "
                  f"({time.monotonic() - start:.1f} s).")
            return huizen
        if time.monotonic() >= volgende_melding + 10:
            volgende_melding = time.monotonic()
            print(f"[INFO] Nog aan het zoeken... ({poging} pogingen)")

    raise GeenSchemaGevonden(
        f"Na {max_seconden:.0f} seconden ({poging} pogingen) geen geldig schema gevonden. "
        "Mogelijk zijn de eisen te streng, bijvoorbeeld lage maximale aantallen bezoekers, "
        "veel 'geen kinderen' of te weinig huizen. Laat je de vorige editie meetellen, "
        "probeer het dan eens zonder (--vorige geen).")


# ----------------------------------------------------------------------------
# Onafhankelijke controle
# ----------------------------------------------------------------------------

def controleer_schema(huizen: list, vorige_keer=None) -> list:
    """Controleer alle regels op de ingevulde Huis-objecten. Geeft een lijst fouten."""
    fouten = []
    per_adres = {h.adres: h for h in huizen}

    for h in huizen:
        if h.gang not in GANGEN:
            fouten.append(f"{h.adres} kookt geen (geldige) gang")
        elif h.gang not in h.voorkeur_gangen:
            fouten.append(f"{h.adres} kookt {h.gang}, maar dat staat niet in de voorkeur")

    tafels = {}  # (gang, koker_adres) -> lijst gasten
    for gang in GANGEN:
        for h in huizen:
            waar = getattr(h, gang)
            koker = per_adres.get(waar)
            if h.gang == gang:
                if waar != h.adres:
                    fouten.append(f"{h.adres} kookt {gang} maar eet die gang bij {waar}")
            elif koker is None or koker.gang != gang:
                fouten.append(f"{h.adres} eet {gang} bij {waar}, maar daar wordt geen {gang} gekookt")
            else:
                tafels.setdefault((gang, waar), []).append(h)

    vorige = {(normaliseer_adres(k), normaliseer_adres(g)) for k, g in (vorige_keer or ())}
    for koker in huizen:
        gasten = tafels.get((koker.gang, koker.adres), [])
        if not 1 <= len(gasten) <= MAX_GASTEN:
            fouten.append(f"{koker.adres} ontvangt {len(gasten)} huizen (moet 1 t/m {MAX_GASTEN} zijn)")
        personen = sum(g.aantal_personen for g in gasten)
        if personen > koker.max_eters:
            fouten.append(f"{koker.adres} ontvangt {personen} personen, maximum is {koker.max_eters}")
        for g in gasten:
            if g.kids_mee and not koker.kids_welkom:
                fouten.append(f"{g.adres} neemt kinderen mee naar {koker.adres}, waar dat niet kan")
            if (normaliseer_adres(koker.adres), normaliseer_adres(g.adres)) in vorige:
                fouten.append(f"{koker.adres} kookte vorige keer ook al voor {g.adres}")

    ontmoetingen = {}
    for (gang, koker_adres), gasten in tafels.items():
        aan_tafel = sorted([koker_adres] + [g.adres for g in gasten])
        for paar in combinations(aan_tafel, 2):
            ontmoetingen.setdefault(paar, []).append(gang)
    for (a, b), gangen in ontmoetingen.items():
        if len(gangen) > 1:
            fouten.append(f"{a} en {b} zitten vaker samen aan tafel ({', '.join(gangen)})")

    met_kids = [h.adres for h in huizen if h.kids_mee]
    if len(met_kids) >= 2:
        for adres in met_kids:
            if not any(tuple(sorted((adres, ander))) in ontmoetingen
                       for ander in met_kids if ander != adres):
                fouten.append(f"{adres} (met kinderen) ontmoet geen ander gezin met kinderen")

    return fouten
