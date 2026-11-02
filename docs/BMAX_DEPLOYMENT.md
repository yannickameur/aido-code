# BMAX deployment and rollback

## Release gates

AIDO Code v0.2.3 requires engine v0.2.2. Both packages are distributed through
GitHub Releases with wheel, sdist and SHA256SUMS; no PyPI publication.
WI-M3.6-01/02 completed through the stable installed controller. Governed QA
passed 461 frontend tests on `904195e`; the installed wheel also passed 461.
The engine suite passed 1541 tests. PR #19 and its rebased main `be76fc6`
passed Python 3.10/3.12 CI; their Git trees are identical.

Published releases: [AIDO Code v0.2.3](https://github.com/yannickameur/aido-code/releases/tag/v0.2.3)
and [engine v0.2.2](https://github.com/yannickameur/ai-dev-orchestrator/releases/tag/v0.2.2).
Downloaded artifacts match the tested bytes and published checksums.

On 2026-11-02, `LIVE-QWEN-08` passed with installed wheels: Qwen Developer
committed `0bfa9a6`; distinct Qwen Reviewer completed its review without a
required correction. The sessions did not overlap. Deterministic QA passed
on that SHA; AIDO merged it and tagged `feature/LIVE-QWEN-08/done`.
Tests and governance files were unchanged; no runtime guidance was needed.
Earlier [engine P2 evidence](https://github.com/yannickameur/ai-dev-orchestrator/blob/main/docs/P2_ACCEPTANCE.json)
records a real corrective Qwen review in `LIVE-QWEN-06`.

The new `~/.local/share/aido/venv-0.2.3` is active through both launchers.
Installed command checks and managed-service inference passed. Rollback was
executed: original launchers/registry restored byte-for-byte, old versions
0.2.2/0.2.1 observed, dedicated service stopped. Reactivation then passed.
Structured evidence: [M36_ACCEPTANCE.json](M36_ACCEPTANCE.json).

The runtime still reports the aggregate MVP status as `running` and retains
a historical wait record for WI-M3.6-02, while both WorkItems are `completed`
and no worker is active. These stored historical fields were not rewritten
to manufacture a terminal milestone status.

## Local configuration

Use the global [BMAX registry example](../examples/bmax-workers.yaml).
`qwen_developer` (priority 110) and `qwen_reviewer` (109) use `qwen3.5:9b`.
`selection.preferred_provider: ollama` is explicit global opt-in. Capability,
availability and distinct worker identity remain mandatory; cloud workers
remain available for fallback. Projects contain no worker/provider policy.

The BMAX deployment retains the operator's previous cloud configuration,
including disabled Mistral workers after noninteractive approval stalls.
Packaged defaults retain their original cloud pool.

The dedicated loopback endpoint uses the existing model storage with:

```text
OLLAMA_HOST=127.0.0.1:11435
OLLAMA_CONTEXT_LENGTH=16384
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
OLLAMA_KEEP_ALIVE=2m
OLLAMA_VULKAN=1
OLLAMA_IGPU_ENABLE=1
```

The launchers set `CODEX_OSS_BASE_URL` to this endpoint's `/v1` URL unless
explicitly overridden. The shared HA-AI Ollama system service is unchanged.
The dedicated user service is `aido-ollama.service`; it starts with the user
session. User lingering is not enabled by this deployment.

## Inference failure and recovery

`LIVE-QWEN-07` encountered Ollama `prediction aborted, token repeat limit
reached`: tests alone did not complete the DEV phase, and AIDO refused PASS.
The operator interrupted the recovery attempt. Restarting only the dedicated
Ollama process restored the identical tool-call probe, both with default
thinking and with thinking disabled. This observation does not establish the
upstream root cause. Model, worker registry and context settings stayed unchanged.
No raw model reasoning is included in published evidence.

For the same failure: interrupt through AIDO, verify no worker remains, restart
only `systemctl --user restart aido-ollama.service`, check the endpoint and model,
then resume through `aido run`. Never edit SQLite or fabricate business events.

## Rollback

The old venvs are preserved. Before activation, backups of `aido`, `aido-code`
and the global registry are stored under:

```text
~/.local/share/aido/rollback/pre-0.2.3/
```

Stop any AIDO run normally, then execute `rollback.sh` in that directory.
It restores both launchers and the compatible registry and stops/disables only
the dedicated user service. Verify `aido version` and `aido status` afterwards.
Do not downgrade packages inside either installed environment.
