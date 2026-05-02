"""CLI entry point. Run with `python -m fante`."""

import argparse

from pydantic import ValidationError

from fante.compose import build_game


def main() -> int:
    parser = argparse.ArgumentParser(description="Fante — aventura de rol por terminal")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Borra la sesión guardada y empieza desde cero.",
    )
    args = parser.parse_args()

    try:
        game = build_game(reset=args.reset)
    except FileNotFoundError as exc:
        print(f"No se encontró el archivo de perfil: {exc}")
        return 1
    except ValidationError as exc:
        print(f"Perfil inválido: {exc}")
        return 1

    game.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
