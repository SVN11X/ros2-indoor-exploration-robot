# 0003. Git LFS for large mapping session files

- Status: accepted
- Date: 2026-11-20
- Proposed by: Claude Code
- Accepted by: owner, in the Claude Code session of 2026-11-20

## Context

`experiments/sesiones_mapeo/` holds six pose graphs of 6.7 to 6.8 MB and a SLAM replay log of 5.5 MB. The standard keeps files over 5 MB out of plain git. These files are evidence the thesis cites.

## Decision

- `.gitattributes` sends `*.posegraph` and `*_slam_replay.log` to Git LFS. That covers the 6 pose graphs and the 6 replay logs.
- History is not rewritten. Older commits keep the plain blobs.
- Before the change, each log was restored to its exact committed bytes. The SHA-256 of every LFS object matches the previous blob.

## Alternatives considered

- Remove the files from git and keep them only on disk. The folder the thesis cites would be incomplete on GitHub.
- Rewrite history with `git lfs migrate`. It would shrink the repository, but every clone would break.

## Consequences

- Every machine needs `git lfs install` once before `git pull`. Without it, the files appear as small text pointers.
- To undo it, remove the two LFS lines from `.gitattributes` and run `git add --renormalize .`.
