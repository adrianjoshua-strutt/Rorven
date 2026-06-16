# Memory architecture

## Memory categories

### Run state

Ephemeral execution state such as plans, open tasks, child results, and pending tool calls. Owned by the runtime/checkpoint layer.

### Project memory

Durable typed knowledge shared across runs. Accessed only through `MemoryBackend`.

### Repository knowledge

Regenerable indexes and summaries derived from project files. Not authoritative project memory.

## Memory record

A memory record should contain:

- ID
- project scope
- type
- content
- provenance
- created-by agent/run
- confidence
- status
- timestamps
- supersedes/superseded-by references
- tags

## Initial memory types

- architecture decision summary
- coding convention
- repository fact
- important file
- failed approach
- environment fact
- user instruction
- unresolved issue
- run summary

## Rules

- Memory is visible and editable in the UI.
- Memory can be invalidated or superseded.
- Normative repository documents override memory.
- Agents use memory tools and never depend on a concrete backend.
- Automatic memory extraction is optional and policy-controlled.
