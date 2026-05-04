"""Slash command handler for the game REPL.

`CommandHandler` is callable: `handler(line) -> str | None`.
- Returns a string  → emit it, skip the narrator for this turn.
- Returns None      → not a slash command, fall through to the narrator.
- Raises QuitRequested → break the game loop.

Commands implemented:
  /status            — turn count, player name, session age, current mode
  /roll <spec>       — dice roll (e.g. /roll 2d6+3)
  /check <rule_id> [json_context] — action check via rules backend
  /dice              — switch to dice mode for this session
  /skill             — switch to skill mode for this session
  /save              — force-persist the current session
  /reset             — clear history and session
  /quit              — exit the game
"""

import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, Literal

from fante.domain.actor import profile_to_actor
from fante.domain.profile import PlayerProfile
from fante.manager import QuitRequested
from fante.ports import RulesPort

Mode = Literal["dice", "skill"]


class CommandHandler:
    """Processes slash commands on behalf of the game loop.

    Accepts callables instead of a GameManager reference to avoid a
    circular dependency between cli and manager.
    """

    def __init__(
        self,
        profile_name: str,
        get_turn_index: Callable[[], int],
        get_session_started_at: Callable[[], datetime],
        reset_fn: Callable[[], None],
        save_fn: Callable[[], None],
        rules_port: RulesPort | None = None,
        get_profile: Callable[[], PlayerProfile] | None = None,
        get_mode: Callable[[], Mode] | None = None,
        set_mode: Callable[[Mode], None] | None = None,
    ) -> None:
        self._profile_name = profile_name
        self._get_turn_index = get_turn_index
        self._get_session_started_at = get_session_started_at
        self._reset_fn = reset_fn
        self._save_fn = save_fn
        self._rules = rules_port
        self._get_profile = get_profile
        self._get_mode = get_mode
        self._set_mode = set_mode

    def __call__(self, line: str) -> str | None:
        if not line.startswith("/"):
            return None
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd == "/quit":
            raise QuitRequested
        if cmd == "/status":
            return self._status()
        if cmd == "/reset":
            return self._reset()
        if cmd == "/save":
            return self._save()
        if cmd == "/roll":
            return self._roll(arg)
        if cmd == "/check":
            return self._check(arg)
        if cmd == "/dice":
            return self._set_mode_cmd("dice")
        if cmd == "/skill":
            return self._set_mode_cmd("skill")
        return None  # unknown /command — let narrator handle it

    # ------------------------------------------------------------------

    def _status(self) -> str:
        age = datetime.now(timezone.utc) - self._get_session_started_at()
        total = int(age.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        mode_str = f" | Modo: {self._get_mode()}" if self._get_mode is not None else ""
        return (
            f"Turno: {self._get_turn_index()} | "
            f"Aventurero: {self._profile_name} | "
            f"Sesión: {h:02d}:{m:02d}:{s:02d}"
            f"{mode_str}"
        )

    def _reset(self) -> str:
        self._reset_fn()
        return "Aventura reiniciada. ¡Todo olvidado!"

    def _save(self) -> str:
        self._save_fn()
        return "Partida guardada."

    def _roll(self, arg: str) -> str:
        if not arg:
            return "Uso: /roll <spec>  (ej: /roll 2d6+3)"
        if self._rules is None:
            return "(El sistema de dados no está disponible.)"
        try:
            result = self._rules.roll(arg)
            return f"🎲 {result}"
        except ValueError as exc:
            return f"Dados inválidos: {exc}"

    def _check(self, arg: str) -> str:
        parts = arg.split(maxsplit=1)
        if not parts:
            return "Uso: /check <rule_id> [json_context]  (ej: /check climb)"
        rule_id = parts[0]
        context: dict[str, Any] | None = None
        if len(parts) > 1:
            try:
                context = json.loads(parts[1])
            except json.JSONDecodeError as exc:
                return f"Contexto JSON inválido: {exc}"

        if self._rules is None:
            return "(El sistema de reglas no está disponible.)"
        if self._get_profile is None:
            return "(Perfil no accesible desde el comando /check.)"
        try:
            actor = profile_to_actor(self._get_profile())
            result = self._rules.check(rule_id, actor, context)
        except NotImplementedError:
            return "Necesitas FANTE_RULES_BACKEND=mcp para usar /check."
        except Exception as exc:
            return f"Error al resolver la acción: {exc}"

        plot = ", ".join(d.value for d in result.plot_dice) or "—"
        seed = result.narration_seed or "—"
        status = "✓ Éxito" if result.success else "✗ Fallo"
        return (
            f"[{result.rule_id} / {result.pack_name}] "
            f"Total: {result.total} vs DC {result.difficulty} → {status}\n"
            f"  Tirada: {result.kept_roll} | Attr: +{result.attribute_bonus} "
            f"| Skill: +{result.skill_bonus} | Sit: {result.situational_modifier:+d}\n"
            f"  Dados de trama: {plot}\n"
            f"  Semilla narrativa: {seed}"
        )

    def _set_mode_cmd(self, mode: Mode) -> str:
        if self._set_mode is None:
            return "(El cambio de modo no está disponible.)"
        self._set_mode(mode)
        labels = {"dice": "dados (d20)", "skill": "habilidad (evaluador)"}
        return f"Modo cambiado a: {labels[mode]}."
