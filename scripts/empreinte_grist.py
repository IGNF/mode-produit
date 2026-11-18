"""Calcule l'empreinte des données issues du Grist (produits.json et images
téléchargées dans public/images/ et public/agents/) et l'écrit dans un fichier
texte suivi par git.

Les images ne sont pas versionnées (.gitignore) : sans cette empreinte, le
remplacement d'une photo dans le Grist ne changerait aucun fichier suivi, donc
ne déclencherait pas de déploiement.

Usage:
    python3 scripts/empreinte_grist.py src/data/empreinte-grist.txt
"""
import hashlib
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCES = [RACINE / "src" / "data" / "produits.json"]
DOSSIERS_IMAGES = [RACINE / "public" / "images", RACINE / "public" / "agents"]


def sha256(chemin: Path) -> str:
    return hashlib.sha256(chemin.read_bytes()).hexdigest()


def main(sortie: str) -> None:
    lignes = []
    for fichier in SOURCES:
        if fichier.exists():
            lignes.append(f"{sha256(fichier)}  {fichier.relative_to(RACINE).as_posix()}")
    for dossier in DOSSIERS_IMAGES:
        if dossier.is_dir():
            for fichier in sorted(p for p in dossier.rglob("*") if p.is_file()):
                lignes.append(f"{sha256(fichier)}  {fichier.relative_to(RACINE).as_posix()}")
    Path(sortie).write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"Empreinte de {len(lignes)} fichiers écrite dans {sortie}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
