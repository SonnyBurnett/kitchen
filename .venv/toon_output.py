
from pathlib import Path

from tabulate import tabulate
import pandas as pd


#
# Te doen: een betere brief maken, waarbij ook duidelijk is hoe laat de koker zijn/haar gasten kan verwachten.
#

def vind_naam(adres, huizen):
    house = next((h for h in huizen if h.adres == adres), None)
    if house:
        return(house.naam)  # Jan de Vries
    else:
        print("Niet gevonden")
    return "niks"


def print_eters(huizen):
    teller = 1
    gelukt = True
    volgorde = {
        "voorgerecht": 0,
        "hoofdgerecht": 1,
        "nagerecht": 2
    }
    huizen = sorted(huizen, key=lambda h: volgorde[h.gang])
    #huizen = sorted(huizen, key=attrgetter("gang"))
    tabel_schema = []
    tabel_schema.append(["naam", "adres", "kookt gang", "eet voorgerecht bij", "eet voorgerecht met",
                    "eet hoofdgerecht bij", "eet hoofdgerecht met", "eet nagerecht bij", "eet nagerecht met", "aantal huizen", "aantal eters"])
    for huis in huizen:
        voor_eters = wie_eet_nog_meer_mee("voorgerecht", huis, huizen )
        hoofd_eters = wie_eet_nog_meer_mee("hoofdgerecht", huis, huizen )
        na_eters = wie_eet_nog_meer_mee("nagerecht", huis, huizen )
        if len(hoofd_eters) > 3 :
            gelukt = False
        tabel_schema.append([huis.get_naam(), huis.get_adres(), huis.get_gang(), huis.get_voorgerecht(),voor_eters,
                             huis.get_hoofdgerecht(), hoofd_eters, huis.get_nagerecht(), na_eters, huis.aantal_huizen, huis.aantal_eters])
        teller += 1
    return tabel_schema, gelukt


def wie_eet_nog_meer_mee(gang, ik, lijst_huizen):
    andere_eters = []
    if gang == "voorgerecht":
        ik_voor = ik.get_voorgerecht()
    if gang == "hoofdgerecht":
        ik_hoofd = ik.get_hoofdgerecht()
    if gang == "nagerecht":
        ik_na = ik.get_nagerecht()

    for huis in lijst_huizen:
        if huis.get_adres() != ik.get_adres():
            if gang == "voorgerecht":
                if ik_voor == huis.get_voorgerecht():
                    andere_eters.append(huis.get_adres())
            if gang == "hoofdgerecht":
                if ik_hoofd == huis.get_hoofdgerecht():
                    andere_eters.append(huis.get_adres())
            if gang == "nagerecht":
                if ik_na == huis.get_nagerecht():
                    andere_eters.append(huis.get_adres())

    return andere_eters




def afronden(lijst_na_nagerecht):
    schema_tabel, gelukt_hoofdgerecht = print_eters(lijst_na_nagerecht)
    maak_email(lijst_na_nagerecht)
    print(tabulate(schema_tabel, headers="firstrow", tablefmt="grid"))
    with open('kitchenroulette_schema.txt', 'w') as f:
        f.write(tabulate(schema_tabel, headers="firstrow", tablefmt="grid"))

# Hoe laat iedereen per gang verwacht wordt, en hoe de gang in het bericht heet.
TIJDEN = {"voorgerecht": "17.00", "hoofdgerecht": "18.30", "nagerecht": "20.00"}
NAAM_IN_BERICHT = {"voorgerecht": "voorgerecht", "hoofdgerecht": "hoofdgerecht", "nagerecht": "dessert"}

# Dieetwensen die eigenlijk "niets bijzonders" betekenen, laten we weg.
GEEN_WENSEN = {"", "geen", "geen bijzonderheden", "nvt", "n.v.t.", "-"}


def gasten_van(koker, huizen):
    """De huizen die bij deze koker de gang komen eten die hij kookt."""
    return [h for h in huizen if h is not koker and getattr(h, koker.gang) == koker.adres]


def maak_bericht(huis, huizen) -> str:
    """Het persoonlijke bericht voor één huis, als tekst."""
    regels = [f"Beste {huis.naam} ({huis.adres}),",
              "",
              f"Jullie zijn geselecteerd voor het maken van het {NAAM_IN_BERICHT[huis.gang]}.",
              f"Jullie ontvangen {huis.aantal_eters} personen."]

    # Wie er komt is een verrassing: daarom wel de wensen, maar niet de namen van de gasten.
    wensen = [g.dieetwensen.strip() for g in gasten_van(huis, huizen)
              if g.dieetwensen.strip().lower().rstrip(".") not in GEEN_WENSEN]
    if wensen:
        regels.append("Opmerkingen en dieetwensen van jullie gasten:")
        regels += [f"  - {wens}" for wens in wensen]
    else:
        regels.append("Jullie gasten hebben geen bijzondere dieetwensen.")

    regels.append("")
    for gang in TIJDEN:
        if gang != huis.gang:  # de eigen gang eten ze thuis
            regels.append(f"Voor het {NAAM_IN_BERICHT[gang]} worden jullie om {TIJDEN[gang]} uur "
                          f"verwacht op {getattr(huis, gang)}.")
    return "\n".join(regels)


BERICHTEN_MAP = "berichten"


def bestandsnaam(adres: str) -> str:
    """'Warder 174A' -> 'Warder_174A.txt' (alleen veilige tekens in de bestandsnaam)."""
    veilig = "".join(t if t.isalnum() or t in "-." else "_" for t in adres.strip())
    return f"{veilig}.txt"


def maak_email(huizen, map_naam=BERICHTEN_MAP):
    """Print het persoonlijke bericht voor ieder huis en sla het op als los bestand.

    Ieder huis krijgt een eigen bestand in de map 'berichten', bijv. berichten/Warder_72.txt.
    Oude berichten van een vorige run worden eerst opgeruimd.
    """
    map_pad = Path(map_naam)
    map_pad.mkdir(exist_ok=True)
    for oud in map_pad.glob("*.txt"):
        try:
            oud.unlink()
        except OSError:
            print(f"[WAARSCHUWING] Kan oud bericht {oud} niet verwijderen")

    for huis in huizen:
        bericht = maak_bericht(huis, huizen)
        print(bericht)
        print()
        (map_pad / bestandsnaam(huis.adres)).write_text(bericht + "\n", encoding="utf-8")
    print(f"[INFO] {len(huizen)} berichten opgeslagen in de map '{map_pad}'")


def maak_excel(huizen):
    df = vul_df(huizen)
    df.to_excel("output.xlsx", index=False)
    print("[INFO] excel gemaakt")


def maak_df():
    df = pd.DataFrame({
        "naam": pd.Series(dtype="string"),
        "adres": pd.Series(dtype="string"),
        "kookt_gang": pd.Series(dtype="string"),
        "eet voorgerecht bij": pd.Series(dtype="string"),
        "eet voorgerecht met": pd.Series(dtype="string"),
        "eet hoofdgerecht bij": pd.Series(dtype="string"),
        "eet hoofdgerecht met": pd.Series(dtype="string"),
        "eet nagerecht bij": pd.Series(dtype="string"),
        "eet nagerecht met": pd.Series(dtype="string"),
        "aantal huizen": pd.Series(dtype="int"),
        "aantal eters": pd.Series(dtype="int"),
        "max eters": pd.Series(dtype="int"),
        "kids welkom": pd.Series(dtype="string"),
        "kids mee": pd.Series(dtype="string"),
        "aantal personen huis": pd.Series(dtype="int"),
    })
    return df


def vul_df(huizen):

    volgorde = {
        "voorgerecht": 0,
        "hoofdgerecht": 1,
        "nagerecht": 2
    }
    huizen = sorted(huizen, key=lambda h: volgorde[h.gang])
    #huizen = sorted(huizen, key=attrgetter("gang"))

    df = maak_df()
    for huis in huizen:
        voor_eters = wie_eet_nog_meer_mee("voorgerecht", huis, huizen)
        hoofd_eters = wie_eet_nog_meer_mee("hoofdgerecht", huis, huizen)
        na_eters = wie_eet_nog_meer_mee("nagerecht", huis, huizen)
        df.loc[len(df)] = {
            "naam": huis.naam,
            "adres": huis.adres,
            "kookt_gang": huis.gang,
            "eet voorgerecht bij": huis.voorgerecht,
            "eet voorgerecht met": voor_eters,
            "eet hoofdgerecht bij": huis.hoofdgerecht,
            "eet hoofdgerecht met": hoofd_eters,
            "eet nagerecht bij": huis.nagerecht,
            "eet nagerecht met": na_eters,
            "aantal huizen": huis.aantal_huizen,
            "aantal eters": huis.aantal_eters,
            "max eters": huis.max_eters,
            "kids welkom": "J" if huis.kids_welkom else "N",
            "kids mee": "J" if huis.kids_mee else "N",
            "aantal personen huis": huis.aantal_personen,
        }
    return df