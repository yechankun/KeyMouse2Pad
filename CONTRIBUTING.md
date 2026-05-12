# Contributing

Thanks for helping improve KeyMouse2Pad. The project keeps the process small:
focused issues, focused PRs, and automated checks for repetitive work.

## Before You Start

- Use Windows for GUI/input-capture changes.
- Use any platform with `g++` and `make` for mapping-engine changes.
- Keep PRs small enough to review in one pass.
- Avoid unrelated formatting churn.

## Local Checks

GUI smoke test:

```powershell
py -3 gui\converter_gui.py --self-test
```

C++ mapping tests:

```sh
make test
```

Build the Windows executable:

```bat
build_exe.bat
```

## Pull Requests

Use this shape:

1. Explain what changed.
2. Explain how you tested it.
3. Mention any behavior or compatibility risk.

CI will run the standard checks. If CI fails, fix the failure before asking for
review unless the failure is unrelated to your change.

## Branch Strategy

KeyMouse2Pad uses a lightweight trunk-based workflow.

- `main` is the stable development branch and should stay releasable.
- Work in short-lived branches named by purpose, such as `fix/f9-toggle`,
  `feat/mapping-editor`, or `docs/windows-setup`.
- Open PRs back into `main`.
- Keep PRs focused on one behavior change, bug fix, or documentation update.
- Avoid long-running integration branches unless a driver/backend experiment
  truly needs isolation.
- Releases are created from `main` by pushing a version tag, for example
  `v0.1.0`.

Recommended branch prefixes:

- `fix/` for bug fixes.
- `feat/` for user-facing features.
- `docs/` for documentation-only changes.
- `ci/` for automation changes.
- `driver/` for Windows driver experiments.

Release tags should be created only after CI is green on `main`.

## Issues

For bugs, include:

- Windows version.
- KeyMouse2Pad version or commit.
- Steps to reproduce.
- Expected behavior.
- Actual behavior.

For feature requests, describe the use case first. Implementation details can
come later.
