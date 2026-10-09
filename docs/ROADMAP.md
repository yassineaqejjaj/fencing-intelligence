# Roadmap

## Done in the current tree

Account, organization, and role checks; clubs, athletes, and bouts; video upload, transcode, and signed playback; human annotations with versions; touches and manual scores; statistics and PDF reports; dataset doctor and local importers; experimental movement and scoreboard heuristics; coaching rules that require a minimum sample count; English and French navigation; licensed athlete identity with CSV import; competition entries, poule sheets, standings, DE draws with referee assignment and bout completion.

## Next

- A review queue that accepts or rejects heuristic suggestions in one action.
- Playwright coverage of phrase marking and calibration.
- Real TLS termination in front of a staging boot (staging ran plain HTTP behind 127.0.0.1; Secure cookies work on localhost because it is a secure context, but a public host needs the Caddyfile exercised).
- SMTP end-to-end against a real relay (code paths verified without a server: dropped mail is logged, invites hand the token back).
- A data-retention schedule: cron for `retention --apply`, backup-set expiry aligned with it, and a written minor-data policy before any U11–U17 pilot.
- A GitHub-hosted run of the CI workflow.
- Pose estimation behind the existing pipeline interface, still labeled experimental until it is evaluated on fencing video.
- Train and evaluate an action model only on data whose license and consent allow it.
- Optional local language model that paraphrases stored observations and cannot add facts.

## Not a substitute for a referee

Scoreboard lights and pose tracks are not official decisions. Priority weapons still need a person to record the phrase.
