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
    "simple.work_item.started": "New task: {work_item}",
    "simple.work_item.completed": "Task completed",
    "simple.work_item.needs_rework": "Task needs rework",
    "simple.dev_a.started": "{worker} is developing…",
    "simple.dev_a.completed": "{worker} finished development",
    "simple.dev_a.neutral": "Development in progress…",
    "simple.dev_b.started": "{worker} is reviewing the code…",
    "simple.dev_b.completed": "{worker} finished reviewing",
    "simple.dev_b.neutral": "Code review in progress…",
    "simple.dev_fix.started": "{worker} is fixing the code…",
    "simple.dev_fix.completed": "{worker} finished the fix",
    "simple.dev_fix.neutral": "Code correction in progress…",
    "simple.qa.started": "Tests in progress…",
    "simple.qa.pass": "Tests passed",
    "simple.qa.fail": "Tests failed",
    "simple.qa.inconclusive": "Tests inconclusive",
    "simple.git.merge_completed": "Code merge completed",
    "simple.run.interruption_requested": "Run interruption requested",
    "simple.run.interrupted": "Run interrupted",
    "simple.phase.interrupted": "Execution interrupted",
    "simple.work_item.failed": "Task failed",
    "simple.work_item.blocked": "Task blocked",
    "simple.work_item.waiting": "Task waiting",
    "simple.work_item.recovery_required": "Task requires recovery",
    "simple.dev_a.failed": "Development failed",
    "simple.dev_b.failed": "Code review failed",
    "simple.dev_fix.failed": "Code correction failed",
    "simple.qa.failed": "Tests failed",
    "simple.waiting_for_provider": "Waiting for an available AI",
    "simple.error": "Error ({kind})",
    "simple.fact.work_item": "task: {value}",
    "simple.fact.worker": "worker: {value}",
    "simple.fact.reason": "reason: {value}",
    "simple.fact.eligible_at": "eligible at: {value}",
    "simple.unknown_item": "unknown task",
    "help.title": "Available commands:",
    "help.toggle_view": "Switch between simplified and detailed views.",
    "help.cmd./quit": "Quit the interface (same as /exit).",
    "help.quit_keys": "Quit when idle (F10 does not depend on Ctrl).",
    "help.ctrl_c": "Interrupt the run; when idle, clear the input, then quit if pressed twice within 2 s.",
    "run.ctrl_c_again": "Press Ctrl+C again within 2 seconds to quit.",
    "help.refresh_quota": "Refresh the AI plan quota panel.",
    "quota.title": "Quotas",
    "quota.refreshing": "Refreshing…",
    "quota.unknown": "unknown",
    "quota.not_reported": "Not reported",
    "quota.not_available": "Not available",
    "quota.reset": "resets: {when}",
    "quota.window_7d": "7 d",
    "times.title": "AI execution time - {milestone}",
    "times.provider": "Provider",
    "times.executed": "Execution time",
    "times.total": "Total AI",
    "times.none": "No execution",
    "times.unknown": "Unknown",
    "times.unknown_executions": "{count} without known duration",
    "times.unavailable": "Execution time summary not available",
    "help.cmd./export": "Write the whole conversation and event history to a text file.",
    "help.select": "Mouse selection: the mouse is captured, so hold Shift while dragging to select with the terminal.",
    "export.done": "Exported to {path}",
    "export.error": "Export failed: {error}",
    "export.header": "AIDO export - session {session_id} - {timestamp}",
    "export.evicted": "Note: {count} older event(s) were evicted from the 2000-entry history and are not included.",
    "export.conversation": "== Conversation and events ==",
    "export.times": "== Latest execution time table ==",
    "export.summary": "== Latest run summary ==",
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
    "status.project": "project",
    "status.session": "session",
    "status.language": "lang",
    "status.view": "view",
    "view.simplified": "simplified",
    "view.detailed": "detailed",
    "status.idle": "idle",
    "status.running": "running",
    "run.cycles_run": "cycles_run",
    "run.all_terminal": "all_terminal",
    "run.reached_max_cycles": "reached_max_cycles",
    "run.work_items": "work items:",
    "run.events": "events:",
    "run.summary": "Run summary",
    "run.busy": "A run is in progress; wait for it to finish (Ctrl+C requests an interruption).",
    "run.interrupt_requested": "Interruption requested; waiting for the engine to stop.",
    "run.idle_ctrl_c": "Input cleared. Press Ctrl+D or type /exit to quit.",
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
    "simple.work_item.started": "Nouvelle tâche : {work_item}",
    "simple.work_item.completed": "Tâche terminée",
    "simple.work_item.needs_rework": "Tâche à reprendre",
    "simple.dev_a.started": "{worker} développe…",
    "simple.dev_a.completed": "{worker} a terminé son développement",
    "simple.dev_a.neutral": "Développement en cours…",
    "simple.dev_b.started": "{worker} vérifie le code…",
    "simple.dev_b.completed": "{worker} a terminé sa vérification",
    "simple.dev_b.neutral": "Vérification du code en cours…",
    "simple.dev_fix.started": "{worker} corrige le code…",
    "simple.dev_fix.completed": "{worker} a terminé sa correction",
    "simple.dev_fix.neutral": "Correction du code en cours…",
    "simple.qa.started": "Tests en cours…",
    "simple.qa.pass": "Tests validés",
    "simple.qa.fail": "Tests en échec",
    "simple.qa.inconclusive": "Tests non concluants",
    "simple.git.merge_completed": "Fusion du code terminée",
    "simple.run.interruption_requested": "Interruption de l'exécution demandée",
    "simple.run.interrupted": "Exécution interrompue",
    "simple.phase.interrupted": "Exécution interrompue",
    "simple.work_item.failed": "Tâche en échec",
    "simple.work_item.blocked": "Tâche bloquée",
    "simple.work_item.waiting": "Tâche en attente",
    "simple.work_item.recovery_required": "Tâche à récupérer",
    "simple.dev_a.failed": "Développement en échec",
    "simple.dev_b.failed": "Vérification du code en échec",
    "simple.dev_fix.failed": "Correction du code en échec",
    "simple.qa.failed": "Tests en échec",
    "simple.waiting_for_provider": "En attente d'une IA disponible",
    "simple.error": "Erreur ({kind})",
    "simple.fact.work_item": "tâche : {value}",
    "simple.fact.worker": "worker : {value}",
    "simple.fact.reason": "raison : {value}",
    "simple.fact.eligible_at": "éligible à : {value}",
    "simple.unknown_item": "tâche inconnue",
    "help.title": "Commandes disponibles :",
    "help.toggle_view": "Basculer entre les vues simplifiée et détaillée.",
    "help.cmd./quit": "Quitter l'interface (comme /exit).",
    "help.quit_keys": "Quitter au repos (F10 ne dépend pas de Ctrl).",
    "help.ctrl_c": "Interrompre l'exécution ; au repos, effacer la saisie, puis quitter si répété sous 2 s.",
    "run.ctrl_c_again": "Appuyez de nouveau sur Ctrl+C dans les 2 secondes pour quitter.",
    "help.refresh_quota": "Actualiser le panneau des quotas des forfaits IA.",
    "quota.title": "Quotas",
    "quota.refreshing": "Actualisation…",
    "quota.unknown": "inconnu",
    "quota.not_reported": "Non communiqué",
    "quota.not_available": "Non disponible",
    "quota.reset": "réinitialisation : {when}",
    "quota.window_7d": "7 j",
    "times.title": "Temps d'exécution IA - {milestone}",
    "times.provider": "Fournisseur",
    "times.executed": "Temps exécuté",
    "times.total": "Total IA",
    "times.none": "Aucune exécution",
    "times.unknown": "Inconnu",
    "times.unknown_executions": "{count} sans durée connue",
    "times.unavailable": "Bilan des temps non disponible",
    "help.cmd./export": "Écrire toute la conversation et l'historique des événements dans un fichier texte.",
    "help.select": "Sélection à la souris : la souris est capturée, maintenez Maj (Shift) en faisant glisser pour sélectionner avec le terminal.",
    "export.done": "Exporté vers {path}",
    "export.error": "Échec de l'export : {error}",
    "export.header": "Export AIDO - session {session_id} - {timestamp}",
    "export.evicted": "Remarque : {count} événement(s) plus ancien(s) ont été évincés de l'historique de 2000 entrées et ne sont pas inclus.",
    "export.conversation": "== Conversation et événements ==",
    "export.times": "== Dernier tableau des temps d'exécution ==",
    "export.summary": "== Dernier résumé d'exécution ==",
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
    "status.project": "projet",
    "status.session": "session",
    "status.language": "langue",
    "status.view": "vue",
    "view.simplified": "simplifiée",
    "view.detailed": "détaillée",
    "status.idle": "inactif",
    "status.running": "en cours",
    "run.cycles_run": "cycles exécutés",
    "run.all_terminal": "tout terminé",
    "run.reached_max_cycles": "maximum de cycles atteint",
    "run.work_items": "tâches :",
    "run.events": "événements :",
    "run.summary": "Résumé de l'exécution",
    "run.busy": "Une exécution est en cours ; attendez sa fin (Ctrl+C demande une interruption).",
    "run.interrupt_requested": "Interruption demandée ; attente de l'arrêt du moteur.",
    "run.idle_ctrl_c": "Saisie effacée. Appuyez sur Ctrl+D ou tapez /exit pour quitter.",
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
