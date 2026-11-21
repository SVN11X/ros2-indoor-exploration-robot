# 0005. Thesis diagrams stay as images with their PowerPoint sources

- Status: accepted
- Date: 2026-11-21
- Proposed by: Claude Code
- Accepted by: the owner, in a Claude Code session on 2026-11-21

## Context

`AGENTS.md` asks for diagrams written as text in Mermaid, and an image only when that is not possible. The owner added the diagrams of the thesis as PNG files with the PowerPoint files that made them. They are the figures the thesis and the defense use, with icons, colors and layouts that Mermaid cannot reproduce.

## Decision

- The thesis diagrams live in `docs/images/diagrams/` as PNG, each one next to its `.pptx` source with the same name.
- A change to a diagram is made in the PowerPoint file and exported again as PNG with the same name.
- New diagrams that are not thesis figures follow the Mermaid rule.

## Alternatives considered

- Redraw every diagram in Mermaid: loses the look of the thesis figures and takes hours for no gain in content.
- Keep only the PNG: a later change would need redrawing from scratch.

## Consequences

- The READMEs show the same figures as the thesis.
- A diagram and its PNG can drift apart if someone edits one and not the other.
- Most PNG files have a transparent background with dark text, so they read poorly with the GitHub dark theme.
