def formater_montant(valeur) -> str:
    entier = int(valeur)
    return f"{entier:,}".replace(",", " ")
