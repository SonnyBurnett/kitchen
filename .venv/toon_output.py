
from tabulate import tabulate
import pandas as pd


#
# Te doen: een betere brief maken, waarbij ook duidelijk is hoe laat de koker zijn/haar gasten kan verwachten.
#

def vind_dieetwensen(adres, huizen):
    # Klopt geen hout van! Neemt volgens mij het voorgerecht als het hoof- of nagerecht moet zijn.
    house = next((h for h in huizen if h.adres == adres), None)
    if house:
        return(house.dieetwensen)  # Jan de Vries
    else:
        print("Niet gevonden")
    return "niks"


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
        print("Beste", huis.naam, huis.adres)
        print("Jullie zijn geselecteerd voor het maken van het", huis.gang)
        print("Jullie ontvangen", huis.aantal_eters, "personen")
        if huis.gang == "voorgerecht":
            #print("Jullie ontvangen", voor_eters)
            for eter in voor_eters:
                print("Opmerkingen", vind_dieetwensen(eter, huizen))
        if huis.gang == "hoofdgerecht":
            #print("Jullie ontvangen", hoofd_eters)
            for eter in voor_eters:
                print("Opmerkingen", vind_dieetwensen(eter, huizen))
        if huis.gang == "nagerecht":
            #print("Jullie ontvangen", na_eters)
            for eter in voor_eters:
                print("Opmerkingen", vind_dieetwensen(eter, huizen))
        print("Voor het voorgerecht worden jullie om 17.00 uur verwacht op", huis.voorgerecht)
        print("Voor het hoofdgerecht worden jullie om 18.30 uur verwacht op", huis.hoofdgerecht)
        print("Voor het dessert worden jullie om 20.00 uur verwacht op", huis.nagerecht)
        print()
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
    print(tabulate(schema_tabel, headers="firstrow", tablefmt="grid"))
    with open('kitchenroulette_schema.txt', 'w') as f:
        f.write(tabulate(schema_tabel, headers="firstrow", tablefmt="grid"))

def maak_email(lijst_na_nagerecht):
    for huis in lijst_na_nagerecht:
        print("Beste", huis.naam, huis.adres)
        print("Jullie zijn geselecteerd voor het maken van het", huis.gang)
        print("Jullie ontvangen", huis.aantal_eters, "personen")
        for eter in huis.lijst_eters:
            print("Dieetwensen en bijzonderheden", eter)
        print("Voor het voorgerecht worden jullie om 17.00 uur verwacht op", huis.voorgerecht)
        print("Voor het hoofdgerecht worden jullie om 18.30 uur verwacht op", huis.hoofdgerecht)
        print("Voor het dessert worden jullie om 20.00 uur verwacht op", huis.nagerecht)
        print()


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