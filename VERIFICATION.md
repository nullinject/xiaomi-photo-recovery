# Publication verification — 2026-09-28

Verified locally on macOS with Python 3.12, using a clean export of the staged
source files (without local configuration, caches or private data).

```sh
python -m pytest -q
python examples/synthetic_demo.py
```

Result: 64 tests passed. The documented offline demonstration also passed.
GitHub Actions is configured for Python 3.11 and 3.12 on Linux; its live status
is available in the repository Actions tab and is separate from these local results.

Secrets screening used `detect-secrets scan --no-verify` on the tracked file set,
plus a review of paths and credential patterns. One high-entropy finding was a synthetic test SHA-256 value, not a credential.

```sh
python -m pip_audit -r requirements-dev.lock --disable-pip --no-deps
```

No known vulnerabilities were reported for the fully resolved locked dependencies
at the time of this check. The audit is advisory-database based, not a guarantee
that dependencies have no vulnerabilities.

## Limits

No physical Android device was accessed. ADB permissions, cache availability and device-specific recovery were not tested.
This is a publication-readiness check, not a complete application security audit.

## CI environment correction

The first Linux run exposed a missing `ffmpeg` executable in the runner. The video
metadata test uses it to generate a synthetic clip. The workflow now installs
Ubuntu ffmpeg (including ffprobe) before running the unchanged tests. Local
verification used an environment where both executables were available.
