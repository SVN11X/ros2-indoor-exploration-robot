# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/2.0.0/) and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- A 60 second video summary of the thesis in the `demo-videos` release, with a GIF preview at the top of the README and in `docs/videos/`.
- The thesis figures in `docs/images/`: diagrams with their source PowerPoint in `diagrams/`, photos of the parts in `components/`, Gazebo and RViz captures, Fusion 360 renders and new photos of the robot. The READMEs show them where they explain the robot, the firmware, the ROS 2 packages and the experiments. `docs/gantt-chart.pdf` holds the project schedule and `mechanical/robot/robot-v2-drawing.pdf` the drawing of the robot.
- 3D models of the built robot (v2), its first chassis design (v1) and 11 parts in `mechanical/`, with renders in the READMEs and STL copies that GitHub shows in 3D. A clone or pull skips the CAD files. `git lfs pull --include="mechanical/**" --exclude=""` downloads them.

### Changed

- `src/` holds only ROS 2 packages. The firmware is in `firmware/`, the launch scripts in `scripts/launch/`, the Raspberry Pi setup scripts in `scripts/robot-setup/` and the thesis experiments in `experiments/`. `docs/thesis-paths.md` maps the old paths the thesis cites.
- Images, cost spreadsheets and setup guides moved into `docs/`.
- Large mapping session files are stored in Git LFS. Run `git lfs install` before `git pull`.
- Images are sorted by topic in `docs/images/` with descriptive names, and the READMEs show them. Duplicates and debugging captures were removed.
- The four edited demo videos are assets of the `demo-videos` release, with GIF previews in `docs/videos/`.

### Removed

- Administrative files, drafts and the Rufus installer are no longer tracked.
