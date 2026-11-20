# 0002. Spanish READMEs with English copies, and Spanish code comments

- Status: accepted
- Date: 2026-11-20
- Proposed by: owner
- Accepted by: owner, in the Claude Code session of 2026-11-20

## Context

The standard asks for repository content in English. The thesis is in Spanish and shows parts of the code, and the code comments are in Spanish.

## Decision

- Every `README.md` is in Spanish. Its English copy is `README.en.md` in the same folder, and each one links to the other.
- The root only allows `README.md`, so the English copy of the root README is `docs/overview.en.md`.
- Code comments stay in Spanish, so the code matches what the thesis shows.
- Upstream READMEs inside `src/third_party/`, `src/articubot_one/` and `src/serial_motor_demo/` keep their original text.
- Other documents written for the standard, such as `docs/goals.md`, are in English.

## Alternatives considered

- Everything in English. Simpler for the standard, but the owner reads the READMEs in Spanish and the comments would no longer match the thesis.

## Consequences

- A README change must update both files.
- To undo it, delete the `README.en.md` files and `docs/overview.en.md`.
