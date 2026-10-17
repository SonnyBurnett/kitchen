"""Kitchen Roulette: maak een schema wie bij wie eet.

Gebruik (of gewoon 'Run' in PyCharm, dan worden de standaardwaarden gebruikt):
    python roulette.py [deelnemers.xlsx] [--vorige deel.txt] [--seed 42]

Te doen:
  - Voorkeur kunnen opgeven voor kinderen bij elkaar
  - Voorkeur kunnen opgeven om samen met iemand te eten
"""

import argparse
import sys

import inlezen
import schema
import toon_output


def lees_argumenten():
    parser = argparse.ArgumentParser(description="Maak een Kitchen Roulette-schema.")
    parser.add_argument("bestand", nargs="?", default=inlezen.STANDAARD_BESTAND,
                        help=f"Excel-bestand met deelnemers (standaard: {inlezen.STANDAARD_BESTAND})")
    parser.add_argument("--vorige", default="deel.txt",
                        help="bestand met de indeling van de vorige keer (standaard: deel.txt; 'geen' = niet meenemen)")
    parser.add_argument("--seed", type=int, default=None,
                        help="getal om hetzelfde schema opnieuw te kunnen maken")
    return parser.parse_args()


def main():
    args = lees_argumenten()

    try:
        huizen = inlezen.lees_deelnemers(args.bestand)
    except inlezen.InleesFout as fout:
        sys.exit(f"[ERROR] {fout}")
    inlezen.toon_samenvatting(huizen)
    vorige_keer = [] if args.vorige.lower() == "geen" else inlezen.lees_vorige_keer(args.vorige)

    try:
        schema.maak_schema(huizen, vorige_keer=vorige_keer, seed=args.seed)
    except schema.GeenSchemaGevonden as fout:
        sys.exit(f"[ERROR] {fout}")

    fouten = schema.controleer_schema(huizen, vorige_keer)
    if fouten:  # zou niet moeten gebeuren; dan zit er een fout in de zoekcode
        sys.exit("[ERROR] Het gevonden schema klopt niet:\n  - " + "\n  - ".join(fouten))
    print("[INFO] Schema gecontroleerd: aan alle regels voldaan.")

    toon_output.afronden(huizen)
    toon_output.maak_excel(huizen)


if __name__ == "__main__":
    main()
