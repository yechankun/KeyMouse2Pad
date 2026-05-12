# Branching

KeyMouse2Pad uses a small-project workflow: keep `main` clean, keep branches
short, and release with tags.

## Default Flow

```text
short-lived branch -> pull request -> CI -> main -> version tag -> release
```

## Branches

- `main`: stable development branch. It should always be close to releasable.
- `fix/*`: bug fixes.
- `feat/*`: user-facing features.
- `docs/*`: documentation-only changes.
- `ci/*`: GitHub Actions or automation changes.
- `driver/*`: Windows driver experiments.

Avoid permanent `develop`, `staging`, or `release/*` branches until the project
actually needs them. They add process cost before they add value.

## Releases

Releases are tag-based:

```sh
git tag v0.1.0
git push origin v0.1.0
```

The release workflow builds `KeyMouse2Pad.exe` and attaches it to the GitHub
Release.

## Maintainer Rule

If a change cannot be reviewed quickly, split it. The best branch strategy for
this project is not clever branching; it is small changes that CI can verify.
