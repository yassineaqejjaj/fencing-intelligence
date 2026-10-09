# Federation roadmap

How Fencing Intelligence earns a pilot with a fencing federation, and what is
already built toward it. Video and heuristics never officiate: the referee's
call stays authoritative and the product only carries evidence.

## Shipped in this tree (federation pilot slice)

- Licensed athlete identity: `license_number` (unique per organization),
  `birth_year`, and `category` (u11–veteran). Duplicates return 409.
- CSV license import (`POST /athletes/import`): creates clubs as needed,
  upserts on license number, reports per-line errors, capped at 2000 rows.
- Competition entries with weapon matching and duplicate protection.
  Withdrawal is refused once the draw exists.
- Poule generation: snake-distributed groups, circle-method round-robin,
  5-touch bouts labeled `Poule A · bout n`.
- Standings from poule bouts only (formula_version 1): victories, then
  indicator, then touches scored. Scheduled bouts do not count.
- DE draw for any power-of-two table: standard 1v8/4v5 seeding, byes advance
  the entered athlete automatically without inventing opponents.
- `POST /competitions/{id}/de/next` advances winners only from completed,
  decisive bouts. A tie refuses with `undecided` until the referee sets the score.
- Referee assignment with a conflict rule: a referee cannot officiate a bout
  involving their own linked athlete record.
- Bout completion (`POST /bouts/{id}/complete`) so the directoire technique
  can close scoresheets.
- Competition workspace UI: entries, poules, standings table, DE draw and
  advancement, per-bout referee picker, completion controls.

## Acceptance criteria for a one-event pilot

1. Two poule sheets and one DE table run entirely from entries; every bout has
   a label, a referee, and a completed score.
2. Standings exported from stored bout scores match the paper scoresheet.
3. No tied DE bout advances without a referee-set score (assert `undecided`).
4. No referee officiates their own club's athlete (assert `referee_conflict`).
5. The post-event report cites only validated records.

## Next, in order

1. **License seasons and affiliation history.** A license belongs to a season
   and a club; add season rollover and duplicate detection across clubs.
2. **Org hierarchy.** Federation → league → club with delegated admins and a
   federation-wide read model. Invitation onboarding for brand-new users.
3. **Poule qualification rules.** Configurable cut (e.g. top 70%) and
   documented tie-break policy; the current id tiebreak must never decide
   qualification on its own.
4. **Challenge workflow.** Flag a timestamp, referee reviews at 0.25× with
   frame stepping, decision logged with reason. Video stays evidence only.
5. **Mobile piste-side capture** with auto-attach to the right bout.
6. **Retention and publication consent** for U18 athletes, including
   export-then-purge per season.
7. **Results exchange**: Engarde-compatible CSV export at minimum; rankings
   come from official results, never from video statistics.
