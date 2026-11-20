# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/2.0.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- `src/` holds only ROS 2 packages. The firmware is in `firmware/`, the launch scripts in `scripts/launch/`, the Raspberry Pi setup scripts in `scripts/robot-setup/` and the thesis experiments in `experiments/`. `docs/thesis-paths.md` maps the old paths the thesis cites.
- Images, cost spreadsheets and setup guides moved into `docs/`.
- Large mapping session files are stored in Git LFS. Run `git lfs install` before `git pull`.

### Removed

- Administrative files, drafts and the Rufus installer are no longer tracked.
