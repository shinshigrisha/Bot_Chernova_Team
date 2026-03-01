# Runbook / Troubleshooting

## Telegram rate limits (429)
Symptoms:
- Delivery attempts failing with 429
Actions:
- Respect retry_after
- Reduce send rate, enable digest, check dedupe
- Ensure sends go through queue, not handlers

## Missing chat/topic bindings
- Alerts are not appearing in expected topic
Fix:
- Check Team bindings in Admin UI
- Verify bot permissions in forum topics

## Ingest failures (CSV/API)
- Batch status FAILED, parse errors
Fix:
- Validate CSV columns against Data Dictionary
- Check timezone assumptions
- Re-run ingestion with corrected file

## ZiZ analytics disabled
Cause:
- zone_code coverage below threshold
Fix:
- Ensure source provides stable zone_code
- Otherwise operate in Store-only mode

## Duplicate scheduled jobs
Cause:
- multiple scheduler instances
Fix:
- single scheduler or distributed lock

## Recalc required
- rules_version changed
Fix:
- run /admin -> Analytics -> Recalculate for date range (queue)
