# Configuration status

The YAML files in this directory are examples for the intended versioned agent
registry. They are not loaded by the current local runtime.

Today, the active runtime source of truth is:

- Agent dispatch definitions: `src/rorven/application/dispatching.py`
- Agent prompt text: `src/rorven/application/agent_prompts.py`
- Persisted model profile IDs: `.rorven/state.json` through the settings API

Do not add a second live configuration path here without an accepted registry
migration plan. The target registry should replace the hardcoded definitions,
not run beside them.
