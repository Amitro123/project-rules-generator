# Project Governance

`project-rules-generator` is currently a **solo-maintainer project**. This
document describes how decisions are made and how that's expected to evolve
as the project grows. It is intentionally short — most of what would
normally go here applies only when a project has multiple maintainers.

## Current model: Benevolent Dictator (with input)

The author and sole maintainer is [Amit Rosen](https://github.com/Amitro123).
All design decisions, merges, and releases go through them.

What this means in practice:

- **PRs** are reviewed and merged by the maintainer. Contributions are
  welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) — but no SLA on review
  time is promised at this stage. Real-world response: usually within a
  few days for small PRs, longer for larger ones.
- **Issues** are triaged by the maintainer. The
  [PROJECT-ROADMAP.md](PROJECT-ROADMAP.md) reflects current priorities;
  items outside the roadmap are welcome to discuss but may be deferred
  or declined.
- **Releases** follow the cadence in [CHANGELOG.md](CHANGELOG.md). The
  project is alpha (`0.x.x`) — see [pyproject.toml](pyproject.toml)
  classifiers. Breaking changes are allowed and will be noted in the
  CHANGELOG.

## Becoming a maintainer

The project is open to additional maintainers as the contributor base
grows. The intended path:

1. Sustained, high-quality contributions over multiple releases
   (PRs that don't need rework, issue triage, helping others in
   discussions).
2. An invitation from the current maintainer to take on a specific area
   (e.g., a subsystem, a release line, or a particular tech-detection
   profile).
3. Onboarding: write access to the repo, included on the
   `MAINTAINERS.md` list, joint review on PRs in the area.

There is no formal voting process at this stage — when the project has
multiple maintainers, this document will be updated with the consensus
process they agree on.

## Decision-making

For now:

- **Architectural changes** (changes to the contract layer in
  `generator/project_profile.py`, the detection precedence in
  `generator/rules/tech-detection/`, or the CI pipeline) — discussed
  in a PR or issue first, then implemented.
- **Bug fixes and small features** — go straight to a PR.
- **Breaking changes** — must be noted in the PR description and the
  CHANGELOG, even for `0.x.x` releases.

## Security

Security issues should NOT be opened as public GitHub issues. See
[SECURITY.md](SECURITY.md) for the private disclosure channel and the
72-hour acknowledgement / 14-day fix SLA.

## Code of conduct

All interactions are governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
The maintainer enforces it across issues, PRs, discussions, and any
direct contact about the project.

## When this document needs to change

This file should be updated when:

- Additional maintainers join (add them to a `MAINTAINERS.md` list and
  describe the area they own).
- The project moves beyond a single repo (governance for a multi-repo
  org has different needs).
- A funding model is introduced (sponsors, grants, paid support — these
  require explicit conflict-of-interest rules).
- The decision-making model changes (e.g., adopting a steering committee
  or lazy consensus).

For now: small project, small process. The goal of this document is to
make the current state legible to contributors and to leave a clear
path for evolution.
