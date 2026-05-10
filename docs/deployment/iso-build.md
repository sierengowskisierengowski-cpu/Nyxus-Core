# NYX ISO Build Pipeline

## Definition

The NYX ISO pipeline is implemented in `iso-builder/` and produces the NYX distribution image containing NYXUS runtime payloads.

## Prerequisites

- Arch Linux host
- Root access
- `archiso` toolchain (`mkarchiso`, `squashfs-tools`, `libisoburn`, `dosfstools`)
- Sufficient temporary disk space for build workspace

## Build Command

```bash
cd iso-builder
sudo ./build-iso.sh
```

## Pipeline Responsibilities

`build-iso.sh` performs the following high-level stages:

1. Preflight validation (host OS/tooling/permissions)
2. Staging of NYXUS payload inputs
3. Staging of desktop configs, launchers, and support scripts into `airootfs`
4. Optional staging of offline cache from `artifacts/api-server/dist/nyxus-scripts`
5. Mirroring root project docs into `airootfs/etc/nyxus/`
6. `mkarchiso` execution and canonical ISO naming

## Inputs and Outputs

### Inputs
- Archiso profile under `iso-builder/nyx-profile/`
- Runtime payload source under `artifacts/api-server/nyxus-scripts/`
- Optional API dist cache under `artifacts/api-server/dist/nyxus-scripts/`

### Output
- `iso-builder/out/nyx-<version>-x86_64.iso`

## Common Caveats

- ISO build is not supported in Replit environments.
- Building without API dist cache produces an online-only first-boot path.
- Build host must be treated as part of release-chain integrity.
