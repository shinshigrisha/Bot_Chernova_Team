# Data Dictionary

## Ingest batches
- `source`: csv_upload | superset_api | db_direct
- `content_hash`: SHA256 file/payload
- `rules_version`: version of business rules used for calc

## delivery_orders_raw (key columns)
- order_key
- ds_code
- courier_key
- service_code
- zone_code (nullable)
- created_at, start_delivery_at, deadline_at, finish_at_raw, finish_at_offline
- durations: wait, assembly, delivery, total (minutes)
- raw (jsonb)

## delivery_orders_calc (derived)
- finish_at_effective
- remaining_pct
- timer_sign (pos/neg/unknown)
- ignore flags (<40% remaining or negative timer)
- is_violation_good_remaining (>50% & pos_timer & late)
- hard-save (<20% & success)
- save+ (20–40 & success)
- assembly_share, is_assembly_blocker
- trip_id, trip_pool, L_pickup, is_dobor, is_negative_dobor

## Zone gating
- `zone_coverage` computed per batch/day.
- If below threshold -> Store-only reporting.
