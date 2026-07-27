# Scenario JSON Schemas (v1)

Formal JSON Schema definitions for YAML scenario files parsed by `crude-scenarios`.

| Schema | Scenario type | Example fixture |
|--------|---------------|-----------------|
| [blend-schedule.v1.json](blend-schedule.v1.json) | Multi-month assay blend LP | `fixtures/scenarios/blend-schedule-tiny.yaml` |
| [inventory.v1.json](inventory.v1.json) | Multi-month inventory procurement LP | `fixtures/scenarios/refinery-inventory.yaml` |
| [static-blend.v1.json](static-blend.v1.json) | Single-period blend evaluate/optimize | `fixtures/scenarios/gulf-coast-slate.yaml` |

Static single-period blend scenarios use `fixtures/scenarios/gulf-coast-slate.yaml` (documented in README).

Validate YAML against schema (requires `yq` + `ajv`):

```bash
yq -o=json fixtures/scenarios/blend-schedule-tiny.yaml | ajv validate -s schemas/blend-schedule.v1.json -d -
```
