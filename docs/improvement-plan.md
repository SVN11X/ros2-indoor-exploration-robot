# Improvement plan

Agreed with the owner on 2026-11-20. Goal: order folders and files with the SVN11X standard. The code is final, so only paths may change, and code comments stay in Spanish.

- [x] Track the 7 files cited in thesis annex 9 that were never committed.
- [x] Commit the owner's deletion of 95 administrative files and drafts that no code uses.
- [x] Adopt the standard: .standard.yml, AGENTS.md, docs base, .github templates, Git LFS for session files, Rufus installer out of git.
- [x] Move imag/, costos/ and robotics_setup/ into docs/images/, docs/costs/ and docs/robot-setup/.
- [x] Move the 5 vendored ROS 2 packages into src/third_party/ and update the m-explore-ros2 path in the explore setup guide.
- [x] Move src/arduino_firmware/ to firmware/ and update the two location comments in pid_config.
- [x] Move src/test/ to experiments/ and update TEST_DIR, OUTDIR, the install depth and the usage comments that point there.
- [x] Move src/prod/ to scripts/launch/ and update the usage lines that print its path.
- [x] Move the 6 Raspberry Pi setup scripts to scripts/robot-setup/ and fix the heck_usb_ports.sh file name.
- [x] Write docs/thesis-paths.md mapping every path cited in thesis annex 9 to its new location.
- [x] Write README.md files in Spanish with real content from the thesis, each with an English copy in a separate file.
- [x] Fill docs/goals.md and docs/how-it-works.md from the thesis, and list third-party packages in docs/credits.md.
- [x] Record decisions: colcon layout, bilingual READMEs, Spanish code comments, Git LFS for session data.
- [x] SKIPPED: formatter, linter, CI tests and pinned dependencies. The code is final and only paths may change.
- [x] Sort the 95 images of docs/images/test/ by topic, rename them, drop duplicates and show them in the READMEs.
- [x] Publish the 4 edited demo videos as release assets with GIF previews in docs/videos/, and sort the local video/ folder.
