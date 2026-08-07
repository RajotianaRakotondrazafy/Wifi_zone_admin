from config.settings import (
    TARIFICATION_PRIX_PAR_HEURE,
    TARIFICATION_DEBIT_DEFAUT_MBPS,
    TARIFICATION_LIBRE_MIN_AR,
    TARIFICATION_LIBRE_MIN_MIN,
)
from repositories.parametres_repository import ParametresRepository

_DEFAUTS = {
    "tarif_prix_par_heure":    TARIFICATION_PRIX_PAR_HEURE,
    "tarif_debit_defaut_mbps": TARIFICATION_DEBIT_DEFAUT_MBPS,
    "tarif_libre_min_ar":      TARIFICATION_LIBRE_MIN_AR,
    "tarif_libre_min_min":     TARIFICATION_LIBRE_MIN_MIN,
    "app_refresh_interval_s":  60,
}


class ParametresController:
    def __init__(self):
        self._repo = ParametresRepository()

    def charger(self) -> dict[str, int]:
        return {cle: self._repo.get_int(cle, defaut) for cle, defaut in _DEFAUTS.items()}

    def sauvegarder(self, data: dict[str, int]) -> None:
        for cle, valeur in data.items():
            if cle in _DEFAUTS:
                self._repo.set(cle, str(valeur))

    # ── Accès rapide pour les autres controllers ──────────────────────────

    def tarif_prix_par_heure(self) -> int:
        return self._repo.get_int("tarif_prix_par_heure", TARIFICATION_PRIX_PAR_HEURE)

    def tarif_libre_min_ar(self) -> int:
        return self._repo.get_int("tarif_libre_min_ar", TARIFICATION_LIBRE_MIN_AR)

    def tarif_libre_min_min(self) -> int:
        return self._repo.get_int("tarif_libre_min_min", TARIFICATION_LIBRE_MIN_MIN)

    def tarif_debit_defaut_mbps(self) -> int:
        return self._repo.get_int("tarif_debit_defaut_mbps", TARIFICATION_DEBIT_DEFAUT_MBPS)

    def app_refresh_interval_s(self) -> int:
        return self._repo.get_int("app_refresh_interval_s", 60)
