# Optagelser: GSearch og Bifrost side om side

Rå svar fra GSearch v2.0 og Bifrost (testmiljøet `bifrost.test42.dataforsyningen.dk`)
for de samme søgestrenge, optaget på samme tidspunkt (`recorded_at`, UTC), før GSearch
lukker i november 2026. Én fil pr. søgestreng (og evt. kommunekoder):

- `gsearch.requests`: ét opslag pr. GSearch-ressource (alle 13, også dem pluginet ikke
  bruger, fx `navngivenvej`), `limit=10`, med URL (token erstattet af `REDACTED`).
- `bifrost.requests`: `/resolve` og `/search` for hvert target, med request-body.
  Med kommunekoder hentes 100 hits pr. target, fordi Bifrost ikke kan filtrere på kommune.
- `sources`: hvor søgestrengen kommer fra (sammenligningssiden, `tests/cases.yaml`, ...).

Geometrier med mere end 250 punkter er gemt som et resumé (type, bbox, antal punkter,
areal/længde). Optaget med `tests/tools/record_differences.py`.
