---
name: simready-package
description: >
  Guide a user from a folder of USD files to a validated SimReady package:
  set up the venv (including the user-provided WRAPP wheel) and then run
  ``create_simready_package.py``, which performs pre-validation, build,
  and post-validation in one shot.
triggers:
  - validate my SimReady asset
  - validate my SimReady folder
  - package my SimReady asset
  - create a SimReady package
  - publish a SimReady package
  - check if my folder can be packaged
  - SimReady packaging workflow
tools:
  - bash
  - python
dependencies:
  - python >=3.10
  - a locally downloaded WRAPP 2.2.0 wheel from NGC
---

# SimReady Packaging Skill

Drive the end-to-end packaging workflow in `simready_foundations/nv_core/package_sample/`
for a user who wants to publish a folder of USD files as a SimReady package.

## When to Use

Use this skill when the user asks to validate, package, or publish a folder
of USD files as a SimReady package — or when they mention "WRAPP", "SimReady
package", or `create_simready_package.py`.

Do **not** use it for general-purpose USD validation or for validating
packages that were not produced through `create_simready_package.py` in this
sample.

## Overview

The workflow has two stages from the agent's perspective:

```
0. Bootstrap the venv   ──►   1. Run create_simready_package.py
   (one-time)                   (pre-validate ─► build ─► post-validate)
```

The sample directory is `simready_foundations/nv_core/package_sample/`.
Every command below is invoked from that directory with the venv activated.

`create_simready_package.py` drives the three workflow phases internally
— drive **it**, not the underlying modules. The `sr_pkg_sample.*` Python
API exists for users who want to wire the workflow into their own tooling
and is documented in the README; an agent doing command-line work should
always go through `create_simready_package.py`.

## Stage 0 — Bootstrap the venv

This is the hardest part of the workflow. Work through it carefully and
confirm each precondition before running anything.

1. **Check for an existing venv.** If `simready_foundations/nv_core/package_sample/.venv/`
   already exists AND the user can activate it and `import simready.validate`
   and `import wrapp` succeed, skip to stage 1. Otherwise continue.

2. **Locate the WRAPP wheel.** WRAPP (`omni-wrapp-minimal`) is not on
   the default public index. Ask the user if they already have the
   wheel downloaded. If yes, confirm it exists (`test -f "$path"`).
   If no, point them at the NGC download page:
   https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/resources/wrapp_clt/files?version=2.2.0
   (free NGC account; file is `omni_wrapp_minimal-2.2.0-py3-none-any.whl`).

3. **Run the setup script** from the sample directory:
   ```bash
   cd simready_foundations/nv_core/package_sample
   ./setup_venv.sh --wrapp-wheel /path/to/omni_wrapp_minimal-2.2.0-py3-none-any.whl
   ```
   For development setups (private package index or locally built
   wheels), the script also accepts `--extra-index <url>` and
   additional `--*-wheel` flags — see the
   [README](README.md#development-alternative-package-sources).

   The script:
   - creates `.venv/` right next to itself (i.e. inside
     `simready_foundations/nv_core/package_sample/.venv/`),
   - installs `simready-validate` (which pulls in
     `omniverse-asset-validator`, `omniverse-usd-profiles`, etc. as
     declared dependencies) from the public index at
     `https://pypi.nvidia.com/` (no VPN needed),
   - installs WRAPP with the `[local]` extra so it can talk to local
     `file://` repos (other extras — `nucleus`, `s3`, `azure`,
     `storage-api` — are documented in the README and can be layered
     on top with a follow-up `pip install`),
   - installs `pytest`,
   - runs `wrapp version` and fails the bootstrap if the Local File
     System backend is DISABLED.

4. **Activate.** From `simready_foundations/nv_core/package_sample/`,
   source the venv for every subsequent command:
   ```bash
   source .venv/bin/activate
   ```

Common failures:
- *"Could not find a version that satisfies the requirement ..."* —
  the package is not available on the default indexes. If the user has
  access to an additional package index, re-run with
  `--extra-index <url>`. Otherwise check network connectivity to
  `pypi.nvidia.com`.

If two consecutive retries fail, hand control back to the user and point
them at the [human README](README.md). Do not keep trying.

## Stage 1 — Run `create_simready_package.py`

Collect the five positional arguments **and** the `--root-usd` flag from
the user. Prompt for any that are missing:

1. `<name>` — package name, e.g. `apple_a01`. Lowercase, no spaces.
2. `<version>` — version string, e.g. `1.0.0`.
3. `<license>` — [SPDX identifier](https://spdx.org/licenses/). If the
   user is unsure, ask what license applies to the asset they are
   publishing. Common public-use choices: `Apache-2.0`, `MIT`,
   `CC-BY-4.0`, `CC-BY-NC-4.0`. For proprietary or bespoke licenses, a
   `LicenseRef-<identifier>` expression is appropriate. Do **not** pick a
   license on the user's behalf.
4. `<source>` — the folder that contains the USDs (and every file they
   reference) the user wants to publish.
5. `<repo>` — a WRAPP repository. Either a local directory path (e.g.
   `/tmp/my_repo` or `~/my_repo`) or a `file://` URL.
6. `--root-usd PATH` — the relative path (inside `<source>`) of each
   root USD entry point (repeatable).  **Required** unless
   `.metadata/com.nvidia.simready.root_usds.json` already exists in
   `<source>` from a prior run.  If the source intentionally has no
   USD files, pass `--no-usd-files` instead.

Then run:

```bash
python create_simready_package.py <name> <version> <license> <source> <repo> \
    --root-usd <relative/path/to/root.usd>
```

The script runs three phases in order:

1. **Pre-validation** (`Package-Candidate` profile) — does `<source>`
   look like something we can package?
2. **Create** — actually build the package via WRAPP and emit the
   SimReady metadata.
3. **Post-validation** (`Package` profile) — does the freshly built
   package conform?

It exits `0` only if every phase that ran exited `0`. On failure it
returns the non-zero exit code of the first phase that failed; the
output identifies which phase that was.

### Interpreting failures

| First failing phase | Headline check | What to tell the user |
|---------------------|----------------|-----------------------|
| Pre-validation | `FET031_PACKAGE_SELF_CONTAINED` | The source failed `AA.001` (anchored asset paths) — at least one USD reference points outside the source folder. Quote the offending path from each `FAIL <FET>: <usd>` line and link to [anchored-asset-paths.md](../sr_specs/docs/capabilities/core/atomic_asset/requirements/anchored-asset-paths.md). Typical fix: change absolute or search paths to `./relative/...`. Offer to open the offending USD; do **not** rewrite USD paths automatically. |
| Pre-validation (exit 2) | "no root USD files specified" | The user forgot `--root-usd`. Ask them for the relative path(s) of the entry-point USD(s) inside `<source>`. If the folder intentionally has no USDs, suggest `--no-usd-files`. |
| Pre-validation (exit 2) | other `UsageError` | The source path doesn't exist or isn't a directory. |
| Create | "source folder is already a WRAPP package with name '<existing>'" | The source root carries a `.<existing>.wrapp` marker from a previous build. The user can either delete that marker, or rerun with `<existing>` as the package name. Surface the error verbatim — it names both the file and the existing package. |
| Create | "contains installed WRAPP subpackages (...); nested packages are not yet supported" | The source has one or more `.wrapp` files in **subfolders** (the root check above only catches the root). Nested packages aren't part of the standard yet; ask the user to remove the nested `.wrapp` files before retrying. |
| Post-validation | `FAIL FET030_PACKAGING_CORE` | The package definition itself is malformed (hashes, metadata entries, file references). Cite the failing requirement code from the output. |
| Post-validation | `FAIL FET032_PACKAGING_INTROSPECTION` | The BOM is missing or invalid. For a package freshly made by the create step this typically means the BOM write was skipped — re-run `create_simready_package.py`. |

On full success the script prints a `Wrote ...:` line for each
metadata file plus an `OK: created <name> <version>` line, and the
post-validation summary lists `PASS` for every `Package`-profile
feature.

### Conformance metadata trust handoff

In the default full flow, pre-validation writes `.metadata/` files
(BOM, root_usds, conformance JSONs with `content_hash`) into the
source folder.  The create step recomputes `content_hash` from the
current source and compares — a match proves the source hasn't
changed since pre-validation, so the conformance results are
registered in the package definition's `metadata` array (covered by
`package_hash`).  A mismatch aborts with a clear error.

Post-validation writes an "evidence" conformance JSON that records the
`Package`-profile result.  Evidence files are **not** covered by
`package_hash` (they are post-creation artefacts).

When `--skip-pre-validation` is used, the create step still looks for
existing `.metadata/conformance.*.json` files.  If found and the
`content_hash` matches, they are registered; if not found, the package
definition carries only the BOM entry.

### Skipping a phase

Two opt-out flags let the user skip individual phases when they have
already done that work or want to defer it:

- `--skip-pre-validation` — go straight to the build. Suggest only
  when the user has just run `--only-pre-validation` against the same
  source folder.  The create step still verifies any existing
  `.metadata/` conformance files.
- `--skip-post-validation` — stop after the build. Suggest when the
  user plans to validate the published package later (e.g. on a
  different machine).

### Single-phase modes

Two `--only-*` modes run a single phase. They are mutually exclusive
with each other and with the default flow — positional arguments are
rejected, and the matching `--source` / `--package-def` flag is
required:

- `--only-pre-validation --source <folder> --root-usd <path>` —
  pre-flight only.  Useful while iterating on `AA.001` errors before
  the user is ready to build.  `--root-usd` is required (same rules
  as the default flow).
- `--only-post-validation --package-def <path>` — `Package`-profile
  validation only. Useful for re-checking a package the user (or
  someone else) published earlier.

### `--no-wrapp` (no-WRAPP fallback)

If the user does not have (or cannot install) the WRAPP wheel, or
explicitly says they only need a minimal package skeleton, the
`--no-wrapp` flag swaps the build phase for a WRAPP-less alternative
that writes a single `com.nvidia.simready.packaging.json` (required
fields only — no BOM, no `.metadata/`, no file hashes) directly into
the `<source>` folder. The source folder *is* the package in this
mode, so the `<repo>` positional argument is dropped:

```bash
python create_simready_package.py <name> <version> <license> <source> --no-wrapp
```

Important caveats to surface to the user before suggesting this
mode:

- The resulting package will FAIL post-validation features that
  inspect the BOM (e.g. `FET032_PACKAGING_INTROSPECTION`). That is
  expected. Combine with `--skip-post-validation` when you want a
  clean exit.
- This is the right answer for "I just need a SimReady-stamped
  folder for a quick demo / experiment" or "I cannot install WRAPP
  in this environment" — not for actual publication. If the user
  intends to publish the package, steer them back to the full
  WRAPP-driven default flow.

## Notes for the Agent

- The script exits `0` on success. Do not assume success from stdout
  alone — always inspect `returncode`.
- Activate the venv once at the start of the conversation and remind
  the user it must remain active across commands.
- The tests under `tests/` exist as a reference; you should not need to
  run pytest for the packaging workflow itself, only when debugging the
  scripts.
- Never modify the user's USD files; only read them. Suggest fixes in
  plain English.
- Conformance metadata (`.metadata/` files) and root-USDs metadata
  are produced automatically by the default full flow.  The user can
  control them with `--write-metadata` and `--write-evidence`.
- The Python API under `sr_pkg_sample/` exists for users who want to
  embed the workflow in their own tooling. As an agent doing command-line
  work, always drive `create_simready_package.py`.
