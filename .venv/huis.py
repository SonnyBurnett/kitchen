"""Het Huis: één deelnemende groep (meestal een gezin) aan de Kitchen Roulette."""

from dataclasses import dataclass, field

GANGEN = ("voorgerecht", "hoofdgerecht", "nagerecht")


@dataclass
class Huis:
    # --- Gegevens uit het inschrijfformulier (Excel) ---
    adres: str
    naam: str
    aantal_personen: int
    max_eters: int                  # max. aantal personen dat dit huis wil ontvangen
    voorkeur_gangen: frozenset      # gangen die dit huis wil koken, bijv. {"voorgerecht"}
    kids_welkom: bool               # mogen er kinderen op bezoek komen?
    kids_mee: bool                  # neemt deze groep zelf kinderen mee?
    dieetwensen: str = ""

    # --- Wordt ingevuld tijdens het maken van het schema ---
    gang: str = ""                  # de gang die dit huis kookt
    voorgerecht: str = ""           # adres waar het voorgerecht gegeten wordt
    hoofdgerecht: str = ""
    nagerecht: str = ""
    aantal_eters: int = 0           # aantal bezoekers (personen) bij dit huis
    aantal_huizen: int = 0          # aantal bezoekende groepen bij dit huis
    lijst_eters: list = field(default_factory=list)  # adressen die dit huis al heeft ontmoet

    @property
    def voorkeur_code(self) -> str:
        """Voorkeur als 'JNN'-code (voorgerecht, hoofdgerecht, nagerecht)."""
        return "".join("J" if g in self.voorkeur_gangen else "N" for g in GANGEN)

    # ------------------------------------------------------------------
    # Getters/setters die de rest van het programma nog gebruikt.
    # Deze kunnen weg zodra roulette.py en toon_output.py zijn opgeschoond.
    # ------------------------------------------------------------------
    def get_naam(self): return self.naam
    def get_adres(self): return self.adres
    def get_gang(self): return self.gang
    def get_voorgerecht(self): return self.voorgerecht
    def get_hoofdgerecht(self): return self.hoofdgerecht
    def get_nagerecht(self): return self.nagerecht
    def get_lijst_eters(self): return self.lijst_eters

    def set_gang(self, gang): self.gang = gang
    def set_voorgerecht(self, adres): self.voorgerecht = adres
    def set_hoofdgerecht(self, adres): self.hoofdgerecht = adres
    def set_nagerecht(self, adres): self.nagerecht = adres

    def add_eter(self, adres): self.lijst_eters.append(adres)
