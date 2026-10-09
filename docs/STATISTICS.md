# Statistics formulas

Version: 1. Implemented in `packages/fencing-domain/src/fencing_domain/statistics.py`.

Only annotations with status `validated` count. Only touches with `validated` and `valid` count. Draft model suggestions do not count. Unvalidated scoreboard candidates do not change participant scores or these figures.

## Counts

- Touches scored: valid validated touches whose scorer is the athlete.
- Touches conceded: valid validated touches whose receiver is the athlete.
- Offensive attempts: validated annotations whose action is marked as an offensive attempt and whose actor is the athlete. Unknown action codes are counted in frequency and are not offensive attempts.
- Offensive successes: those attempts whose outcome is `touch_for`.
- Defensive actions: validated annotations whose action is marked defensive.
- Riposte attempts and successes use the riposte family, with success meaning outcome `touch_for`.
- Counter-attack attempts and successes use the counter-attack family, with the same success rule.

## Rates

`value = numerator / denominator` when `denominator > 0`. Otherwise `value` is null and `reason` is `no_samples`. A null rate is not zero percent.

## Distributions

- Action frequency counts validated annotations by action code.
- Touch target distribution counts scored touches by target. Missing targets increment `missing_target_count` and are omitted from the counts map.
- Conceded target distribution is separate and uses the same missing-target rule.
- Piste position uses bins of width 0.1 on values from 0 to 1. Missing positions increment `missing_position_count`.

## Time

Score progression uses validated score events only. Performance over time groups touches by the bout date. Bouts without a date increment `undated_bout_count` and are left out of the series.

## Empty data

`data_status` is `ok` only when the athlete has a validated annotation as actor, or a validated valid touch as scorer or receiver, inside the current filter. Otherwise it is `no_validated_data`. Clients must not present that state as a performance chart.

When a weapon filter is set, rows whose weapon is missing or different are excluded. If more than one weapon remains and no filter is set, `mixed_weapons` is true and per-weapon blocks are returned.
