#!/usr/bin/env python3
"""Aggiorna i pin per-digest delle immagini pubblicate su GHCR nei file del
repo, dopo che il workflow .github/workflows/release-images.yml le ha
ricostruite e ripubblicate. Uso:

    update_pinned_digests.py --webtop <sha256esadecimale>
    update_pinned_digests.py --manager <sha256esadecimale>
    update_pinned_digests.py --webtop <...> --manager <...>

Entrambi gli argomenti sono opzionali e indipendenti: passa solo il digest
che e' effettivamente cambiato in questa run (l'altro, se omesso, lascia i
file che lo riguardano intatti). Ogni sostituzione verifica il numero di
occorrenze attese prima di scrivere, cosi' un refactor dei file bersaglio che
rompe silenziosamente il pattern fallisce rumorosamente qui invece di
lasciare il repo con un pin non aggiornato.
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def replace_one(path: pathlib.Path, pattern: str, new_digest: str, expected_matches: int) -> None:
    text = path.read_text()
    matches = list(re.finditer(pattern, text))
    if len(matches) != expected_matches:
        sys.exit(
            f"{path}: attesi {expected_matches} match per {pattern!r}, "
            f"trovati {len(matches)}. Pattern non piu' valido? Aggiorna lo script."
        )

    def sub(m: re.Match) -> str:
        return m.group(0).replace(m.group(1), new_digest)

    path.write_text(re.sub(pattern, sub, text))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webtop", help="Nuovo digest sha256 (senza prefisso 'sha256:') di deskhub-webtop")
    parser.add_argument("--manager", help="Nuovo digest sha256 (senza prefisso 'sha256:') di deskhub-manager")
    args = parser.parse_args()

    if not args.webtop and not args.manager:
        parser.error("passa almeno uno tra --webtop e --manager")

    if args.webtop:
        replace_one(
            ROOT / "backend/app/config.py",
            r'deskhub-webtop"\s*\n\s*"@sha256:([0-9a-f]{64})',
            args.webtop,
            expected_matches=1,
        )
        print(f"backend/app/config.py: pin webtop aggiornato a {args.webtop}")

    if args.manager:
        replace_one(
            ROOT / "install.sh",
            r'deskhub-manager@sha256:([0-9a-f]{64})',
            args.manager,
            expected_matches=1,
        )
        replace_one(
            ROOT / "README.md",
            r'deskhub-manager@sha256:([0-9a-f]{64})',
            args.manager,
            expected_matches=2,
        )
        print(f"install.sh, README.md: pin manager aggiornato a {args.manager}")


if __name__ == "__main__":
    main()
