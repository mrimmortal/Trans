# Scripts

Use these two files only:

```text
run.sh    macOS/Linux helper
run.ps1   Windows helper
```

## Daily Commands

Mac development:

```bash
./scripts/run.sh mac-dev
```

This creates or updates `backend/venv` from `backend/requirements-mac.txt`.

Windows development:

```powershell
.\scripts\run.ps1 win-dev
```

This creates or updates `backend\venv` from `backend\requirements.txt`.

Validate UAT build locally:

```bash
./scripts/run.sh uat-check
```

Validate production build locally:

```bash
./scripts/run.sh prod-check
```

Deploy UAT on the Windows UAT host:

```powershell
.\scripts\run.ps1 uat-win -SourceDir C:\path\to\medical-dictation
```

Deploy production on the Windows production host:

```powershell
.\scripts\run.ps1 prod-win -SourceDir C:\path\to\medical-dictation
```

## GitHub Actions

The pipeline calls `run.ps1 uat-win` and `run.ps1 prod-win` on self-hosted Windows runners.

## Rule

Do not add new top-level scripts unless there is a repeated command that cannot fit into `run.sh` or `run.ps1`.
