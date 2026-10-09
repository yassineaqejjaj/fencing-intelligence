# Decisions

## Application license

Original code is Apache-2.0. Dataset importers are original and read local files the operator already has. GPL-3.0 code from the FIE fencing dataset repository is not copied. Repositories with no license are studied for method only.

## Object storage image

`minio/minio` and `quay.io/minio/minio` could not be pulled anonymously in this environment. Local Compose uses `pgsty/silo` pinned by digest. Silo is a separate S3-compatible server process. Application code talks to it through the S3 API and is not linked against the Silo binary. The Silo image has its own license, distinct from Apache-2.0.

The application does not require that image. `S3_ENDPOINT_URL` can point at any S3-compatible service. `API_PORT` and `WEB_PORT` override the published ports when 8000 or 3000 are already taken.

## Queue

Video jobs use Dramatiq with Redis. Tests and single-process local runs set `INLINE_JOBS=true` so the same function runs in the API process. Production must keep that flag false and run the worker container.

## Statistics

Rates are null when the denominator is zero. The UI must not chart a block whose `data_status` is `no_validated_data`. Weapons are not silently blended into one success rate when more than one weapon is present; `mixed_weapons` is true and `by_weapon` is returned.

## Federation competitions

Poule groups, standings order, and DE seeding live in `fencing_domain.competitions` as documented formulas, not copied rulebook text. Standings count poule bouts only and sort by victories, indicator, then touches scored; the final id tiebreak is arbitrary and must never decide qualification alone. Byes advance the entered athlete without inventing opponents. A tied DE bout refuses to advance until a referee sets a decisive score, and a referee cannot officiate a bout involving their own linked athlete record. License numbers are unique per organization; an empty license means unlicensed, not zero.

## Coaching

Recommendations require at least five validated samples and quote the metric they came from. They do not call a language model. A future local model may paraphrase the stored observation and must not add facts.

## Computer vision

There is no evaluated fencing action model in this repository. The movement module labels speed along a normalized horizontal axis and is marked experimental. Without a declared forward direction it does not emit advance or retreat. The scoreboard module looks for a dominant color channel inside a user-selected region. It does not read digits and does not infer a referee decision.

## Pose estimation

MediaPipe, ONNX, and a pose model are not installed. The pipeline interface exists as later stages. Absence of a pose model is not treated as tactical understanding.

## Sessions

The first registered user becomes administrator of a new organization, which is enough to create clubs and athletes. Invitation acceptance requires an existing account because every session is tied to an organization membership.

## Minors and retention

An athlete is a minor when their birth year makes them under 18. Guardian consent is a `consent_records` row with purpose `guardian_consent` linked to the athlete; the latest record wins, so consent can be revoked. Without a granted record, a minor's video is forced private at upload and `training_consent` is refused, because the platform must not train on athlete video without consent. Soft-deleted videos stay recoverable until `retention --apply` removes their object keys and rows after the configured age; audit rows are append-only and kept. Backups are outside this purge: backup sets must expire on the same schedule, or erasure promises do not hold.
