"""CLI entry point. Run with `python -m fante`."""

from pydantic import ValidationError

from fante.compose import build_game


def main() -> int:
    try:
        game = build_game()
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
