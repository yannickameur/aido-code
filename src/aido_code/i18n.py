"""Deterministic French/English catalog for AIDO Code's own interface texts.

Lookup is a pure function over in-memory dictionaries: no network, no AI,
no I/O. Only the interface's own prose is catalogued. Commands, flags, API
names, WorkItem/worker/session ids, SHAs, paths and raw worker output are
never translated; callers pass them as ``{placeholders}`` values and they
are substituted verbatim."""

from __future__ import annotations

import os
from collections.abc import Mapping
from contextvars import ContextVar, Token

LANGUAGES = ("fr", "en")
DEFAULT_LANG = "fr"
ENV_VAR = "AIDO_LANG"

# The English catalog is the source text and the fallback for any missing key.
EN: dict[str, str] = {
    "help.title": "Available commands:",
    "help.cmd./help": "List available commands.",
    "help.cmd./status": "Show the project's real, persisted status, plus the full worker list.",
    "help.cmd./status --probe": "Same as /status, plus one real provider probe of each worker's state.",
    "help.cmd./workers": "List configured workers (enabled and disabled), no provider probe.",
    "help.cmd./workers --probe": "Same as /workers, plus one real provider probe of each worker's state.",
    "help.cmd./config": "Show the loaded aido.yaml's validated configuration.",
    "help.cmd./validate": "Validate aido.yaml and its worker registry.",
    "help.cmd./run": "Start or resume the project (drives the engine to completion or WAITING).",
    "help.cmd./resume": "Choose an existing session.",
    "help.cmd./new": "Create and switch to a new session.",
    "help.cmd./exit": "Exit the REPL.",
    "input.placeholder": "Ask about status, workers, or what is waiting; or type /help.",
    "not_understood": (
        "Not understood. I can answer: project status, why a WorkItem is waiting/blocked, "
        "which workers/providers are available, or run/continue the project. "
        "Type /help for commands."
    ),
    "unknown_command": "Unknown command: {command}. Type /help for a list of commands.",
    "session.resumed": "Resumed session {session_id}",
    "session.created": "Created session {session_id}",
    "session.none_found": "No sessions found.",
    "session.list_header": "Sessions (most recently used first):",
    "session.no_project": "(no project)",
    "session.select_prompt": "Select a session number (blank to cancel): ",
    "session.cancelled": "Session selection cancelled.",
    "session.invalid": "Invalid session selection.",
    "run.start": "Starting the run.",
    "run.cycles_run": "cycles_run",
    "run.all_terminal": "all_terminal",
    "run.reached_max_cycles": "reached_max_cycles",
    "run.work_items": "work items:",
    "run.events": "events:",
    "run.summary": "Run summary",
    "interrupted": (
        "Interrupted. Output already shown is preserved. The governed engine state "
        "determines recovery: the next `aido run` (or `/run`) calls the engine's "
        "existing recovery path unchanged. `aido resume` and `/resume` only reopen "
        "a session; they do not recover project execution."
    ),
    "diag.title": "diagnostics:",
    "diag.failed_in": "failed in",
    "diag.summary": "summary",
    "diag.next_action": "next action",
    "diag.last_output": "last output",
    "diag.output_display_failures": "output display failures",
    "diag.unrenderable": "(diagnostic could not be rendered)",
    "event.work_item.started": "Work item started",
    "event.work_item.completed": "Work item completed",
    "event.work_item.failed": "Work item failed",
    "event.work_item.waiting": "Waiting for an available AI",
    "event.work_item.recovery_required": "Work item needs recovery",
    "event.dev_a.selected": "Developer A selected",
    "event.dev_a.started": "Developer A started",
    "event.dev_a.completed": "Developer A completed",
    "event.dev_a.failed": "Developer A failed",
    "event.dev_a.interrupted": "Developer A interrupted",
    "event.dev_b.selected": "Developer B selected",
    "event.dev_b.started": "Developer B started",
    "event.dev_b.completed": "Developer B completed",
    "event.dev_b.failed": "Developer B failed",
    "event.dev_b.interrupted": "Developer B interrupted",
    "event.dev_fix.selected": "Developer fix selected",
    "event.dev_fix.started": "Developer fix started",
    "event.dev_fix.completed": "Developer fix completed",
    "event.dev_fix.failed": "Developer fix failed",
    "event.dev_fix.interrupted": "Developer fix interrupted",
    "event.qa.started": "Tests started",
    "event.qa.pass": "Tests passed",
    "event.qa.fail": "Tests failed",
    "event.qa.inconclusive": "Tests inconclusive",
    "event.qa.interrupted": "Tests interrupted",
    "event.run.interrupted": "Run interrupted",
    "event.run.interruption_requested": "Interruption requested",
    "event.git.merge_ready": "Merge ready",
    "event.git.merge_completed": "Merge completed",
    "event.execution.heartbeat": "Still running",
    "event.execution.output_truncated": "Output truncated",
    "event.waiting_for_provider": "Waiting for an available AI",
}

FR: dict[str, str] = {
    "help.title": "Commandes disponibles :",
    "help.cmd./help": "Lister les commandes disponibles.",
    "help.cmd./status": "Afficher l'état réel et persisté du projet, avec la liste complète des workers.",
    "help.cmd./status --probe": "Comme /status, avec une vraie sonde de l'état de chaque worker auprès du fournisseur.",
    "help.cmd./workers": "Lister les workers configurés (actifs et inactifs), sans sonde.",
    "help.cmd./workers --probe": "Comme /workers, avec une vraie sonde de l'état de chaque worker auprès du fournisseur.",
    "help.cmd./config": "Afficher la configuration validée de aido.yaml.",
    "help.cmd./validate": "Valider aido.yaml et son registre de workers.",
    "help.cmd./run": "Démarrer ou reprendre le projet (le moteur tourne jusqu'à la fin ou l'attente).",
    "help.cmd./resume": "Choisir une session existante.",
    "help.cmd./new": "Créer une nouvelle session et y basculer.",
    "help.cmd./exit": "Quitter le terminal.",
    "input.placeholder": "Demandez l'état, les workers ou ce qui est en attente ; ou tapez /help.",
    "not_understood": (
        "Je n'ai pas compris. Je comprends : l'état du projet (status), les workers et fournisseurs "
        "disponibles (workers), pourquoi une tâche est en attente ou bloquée (waiting/blocked), "
        "et lancer ou continuer le projet (run/continue). "
        "Commandes : /help, /status, /workers, /config, /validate, /run, /resume, /new, /exit."
    ),
    "unknown_command": "Commande inconnue : {command}. Tapez /help pour la liste des commandes.",
    "session.resumed": "Session reprise {session_id}",
    "session.created": "Session créée {session_id}",
    "session.none_found": "Aucune session trouvée.",
    "session.list_header": "Sessions (la plus récente d'abord) :",
    "session.no_project": "(aucun projet)",
    "session.select_prompt": "Choisissez un numéro de session (vide pour annuler) : ",
    "session.cancelled": "Sélection de session annulée.",
    "session.invalid": "Sélection de session invalide.",
    "run.start": "Démarrage de l'exécution.",
    "run.cycles_run": "cycles exécutés",
    "run.all_terminal": "tout terminé",
    "run.reached_max_cycles": "maximum de cycles atteint",
    "run.work_items": "tâches :",
    "run.events": "événements :",
    "run.summary": "Résumé de l'exécution",
    "interrupted": (
        "Interrompu. Les sorties déjà affichées sont conservées. L'état du moteur gouverné "
        "détermine la reprise : le prochain `aido run` (ou `/run`) appelle inchangée la "
        "reprise existante du moteur. `aido resume` et `/resume` rouvrent seulement "
        "une session ; ils ne reprennent pas l'exécution du projet."
    ),
    "diag.title": "diagnostics :",
    "diag.failed_in": "échec en phase",
    "diag.summary": "résumé",
    "diag.next_action": "action suivante",
    "diag.last_output": "dernière sortie",
    "diag.output_display_failures": "échecs d'affichage de la sortie",
    "diag.unrenderable": "(diagnostic impossible à afficher)",
    "event.work_item.started": "Tâche démarrée",
    "event.work_item.completed": "Tâche terminée",
    "event.work_item.failed": "Tâche en échec",
    "event.work_item.waiting": "En attente d'une IA disponible",
    "event.work_item.recovery_required": "Tâche à récupérer",
    "event.dev_a.selected": "Développeur A sélectionné",
    "event.dev_a.started": "Développeur A démarré",
    "event.dev_a.completed": "Développeur A terminé",
    "event.dev_a.failed": "Développeur A en échec",
    "event.dev_a.interrupted": "Développeur A interrompu",
    "event.dev_b.selected": "Développeur B sélectionné",
    "event.dev_b.started": "Développeur B démarré",
    "event.dev_b.completed": "Développeur B terminé",
    "event.dev_b.failed": "Développeur B en échec",
    "event.dev_b.interrupted": "Développeur B interrompu",
    "event.dev_fix.selected": "Correction sélectionnée",
    "event.dev_fix.started": "Correction démarrée",
    "event.dev_fix.completed": "Correction terminée",
    "event.dev_fix.failed": "Correction en échec",
    "event.dev_fix.interrupted": "Correction interrompue",
    "event.qa.started": "Tests démarrés",
    "event.qa.pass": "Tests validés",
    "event.qa.fail": "Tests en échec",
    "event.qa.inconclusive": "Tests non concluants",
    "event.qa.interrupted": "Tests interrompus",
    "event.run.interrupted": "Exécution interrompue",
    "event.run.interruption_requested": "Interruption demandée",
    "event.git.merge_ready": "Fusion prête",
    "event.git.merge_completed": "Fusion terminée",
    "event.execution.heartbeat": "Toujours en cours",
    "event.execution.output_truncated": "Sortie tronquée",
    "event.waiting_for_provider": "En attente d'une IA disponible",
}

CATALOGS: dict[str, dict[str, str]] = {"en": EN, "fr": FR}

# Direct library calls retain their established English output. The CLI sets
# this for its interactive session and resets it before returning.
_interactive_lang: ContextVar[str] = ContextVar("aido_interactive_lang", default="en")


def interactive_lang() -> str:
    return _interactive_lang.get()


def set_interactive_lang(lang: str) -> Token[str]:
    return _interactive_lang.set(lang)


def reset_interactive_lang(token: Token[str]) -> None:
    _interactive_lang.reset(token)


class LanguageError(ValueError):
    """An unsupported language value."""


def validate_lang(value: str) -> str:
    if value not in LANGUAGES:
        raise LanguageError(
            f"unsupported language {value!r}; expected one of: {', '.join(LANGUAGES)}"
        )
    return value


def resolve_lang(cli_value: str | None = None, environ: Mapping[str, str] | None = None) -> str:
    """``--lang`` wins over ``AIDO_LANG``, which wins over the default."""
    if cli_value is not None:
        return validate_lang(cli_value)
    env = os.environ if environ is None else environ
    value = env.get(ENV_VAR)
    if value is not None:
        return validate_lang(value)
    return DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG, **values: object) -> str:
    """Pure lookup: unknown language -> English; missing key -> English
    source text; key absent everywhere -> the key itself. ``values`` are
    substituted verbatim and never translated."""
    text = CATALOGS.get(lang, EN).get(key)
    if text is None:
        text = EN.get(key, key)
    return text.format(**values) if values else text


def event_label(kind: object, lang: str = DEFAULT_LANG) -> str | None:
    """The label for a known engine event kind, else ``None`` (callers then
    keep the raw kind)."""
    key = f"event.{kind}"
    return t(key, lang) if isinstance(kind, str) and key in EN else None
