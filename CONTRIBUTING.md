# Contributing

Original code in this repository is licensed under Apache-2.0. By submitting a change you agree that it can be distributed under that license.

- Do not add dataset files, model weights, or code from repositories whose license is missing, unspecified, or GPL-3.0.
- Do not paste FIE or FFE rulebook text. Add a short original label and a source URL.
- Keep statistics formulas in `packages/fencing-domain` and document them in `docs/STATISTICS.md`.
- A new metric must say what happens when the denominator is zero.
- Heuristic or model output stays a draft until a person validates it.
- Add or update a test when you change authorization, statistics, or video processing.
- Do not commit `.env`, videos, or local dataset trees.
