# 0004. A mechanical folder for the 3D models, kept out of normal clones

- Status: accepted
- Date: 2026-11-21
- Proposed by: Claude Code
- Accepted by: the owner, in a Claude Code session on 2026-11-21

## Context

The owner added 23 CAD files of the robot and its parts at the repository root: Fusion 360 sources (.f3d, .f3z), STEP exports, a Blender file and a GLB. Together they weigh about 190 MB, and eight are over 5 MB. The software profile has no folder for CAD. GitHub shows STL files in a 3D viewer up to 10 MB, but not STEP files. Every Git LFS download from a public repository counts against the owner's 10 GiB of monthly LFS bandwidth.

## Decision

- A top-level `mechanical/` folder, named as in the hardware profile of the standard, with `robot/` for the robot designs and `components/` for third-party part models.
- Every CAD source in `mechanical/` goes to Git LFS. `.lfsconfig` sets `lfs.fetchexclude = mechanical/**`, so a clone or pull keeps them as pointer files until someone runs `git lfs pull --include="mechanical/**" --exclude=""`.
- Each robot version has a binary STL copy next to its STEP, under 5 MB and outside LFS, so GitHub shows it in its 3D viewer. The v2 copy is simplified to 90,000 triangles.
- The renders in `docs/images/mechanical/` were made once from the STEP files with cascadio 0.1.1, trimesh and PyVista 0.49.2. The script is not part of the repository, because the models are final.

## Alternatives considered

- Commit the CAD files without LFS: the 5 MB rule blocks it, and every clone would grow by 190 MB.
- LFS without the fetch exclusion: the Raspberry Pi would download 190 MB of models on its next pull, and every clone would spend the owner's LFS bandwidth.
- A release asset, as with the demo videos: keeps the files out of git, but separates them from their documentation and history.
- Keep the third-party models out of the repository: the owner chose to publish them with credits.

## Consequences

- Clones and pulls stay as light as before. Anyone who wants the CAD files runs one command.
- A new version of a model needs a new STEP export, STL copy and render, made by hand.
- To undo the exclusion, remove `.lfsconfig`, and the next pull downloads every model.
