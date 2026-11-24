"""Calcule l'empreinte des données issues du Grist (produits.json, images
téléchargées dans public/images/ et public/agents/, et table Evenements du
document « agenda-public ») et l'écrit dans un fichier texte suivi par git.

Les images ne sont pas versionnées (.gitignore) : sans cette empreinte, le
remplacement d'une photo dans le Grist ne changerait aucun fichier suivi, donc
ne déclencherait pas de déploiement.

L'agenda est lu au build par src/lib/agenda.ts et n'écrit aucun fichier : sans
son empreinte ici, un événement ajouté ou modifié dans le Grist n'apparaîtrait
sur le site qu'au prochain changement des fiches produits.

Usage:
    python3 scripts/empreinte_grist.py src/data/empreinte-grist.txt
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

RACINE = Path(__file__).resolve().parent.parent
SOURCES = [RACINE / "src" / "data" / "produits.json"]
DOSSIERS_IMAGES = [RACINE / "public" / "images", RACINE / "public" / "agents"]

# Document « agenda-public » lu par src/lib/agenda.ts (garder en cohérence).
AGENDA_BASE_URL = os.environ.get("GRIST_BASE_URL", "https://grist.numerique.gouv.fr")
AGENDA_DOC_ID = os.environ.get("GRIST_AGENDA_DOC_ID", "fDwUxVHDoVqQ")
AGENDA_TABLE = os.environ.get("GRIST_AGENDA_TABLE", "Evenements")


def sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def empreinte_agenda() -> str | None:
    """Empreinte des lignes et colonnes de la table Evenements.

    Les colonnes sont incluses car les couleurs des types d'événements
    viennent des options de la colonne Type. Renvoie None sans clé API ;
    lève une exception si Grist ne répond pas, pour ne pas écrire une
    empreinte fausse qui déclencherait un déploiement inutile.
    """
    cle = os.environ.get("GRIST_API_KEY")
    if not cle:
        print("GRIST_API_KEY absente : agenda non pris en compte dans l'empreinte.")
        return None
    session = requests.Session()
    retries = Retry(total=4, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers["Authorization"] = f"Bearer {cle}"
    base = f"{AGENDA_BASE_URL}/api/docs/{AGENDA_DOC_ID}/tables/{AGENDA_TABLE}"
    contenu = {}
    for partie in ("records", "columns"):
        reponse = session.get(f"{base}/{partie}", timeout=30)
        reponse.raise_for_status()
        contenu[partie] = reponse.json()
    brut = json.dumps(contenu, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def main(sortie: str) -> None:
    lignes = []
    for fichier in SOURCES:
        if fichier.exists():
            lignes.append(f"{sha256(fichier)}  {fichier.relative_to(RACINE).as_posix()}")
    for dossier in DOSSIERS_IMAGES:
        if dossier.is_dir():
            for fichier in sorted(p for p in dossier.rglob("*") if p.is_file()):
                lignes.append(f"{sha256(fichier)}  {fichier.relative_to(RACINE).as_posix()}")
    agenda = empreinte_agenda()
    if agenda:
        lignes.append(f"{agenda}  grist:{AGENDA_DOC_ID}/{AGENDA_TABLE}")
    Path(sortie).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"Empreinte de {len(lignes)} sources écrite dans {sortie}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
