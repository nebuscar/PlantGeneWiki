# Repository Cleanup and Data Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove obsolete MySQL work, reproducible caches, and 31.6 GB of ignored data from the repository workspace while preserving verified data archives and provenance records.

**Architecture:** Keep Git focused on code, tests, schemas, small examples, and logical archive records. Copy large datasets to `/DATA/data2/plantgenewiki/archive`, verify complete content before source deletion, and keep machine-specific path mappings in an ignored local configuration file.

**Tech Stack:** Git, Bash, rsync, SHA-256, Python 3 standard library, YAML-compatible configuration, FastAPI unittest suite, Astro/npm.

## Global Constraints

- Never delete a source data directory before its destination passes count, size, rsync checksum, and SHA-256 verification.
- Keep `/home/nizhu/Projects/PlantGeneWiki/.venv/`; it is the active project Python environment.
- Do not commit `/DATA/...` paths, credentials, tokens, `.env` files, caches, raw data, or generated indexes.
- Keep SQLite as the current offline graph snapshot until a formal graph store replaces it.
- Do not delete unaudited files under `scripts/analysis/`, `scripts/importers/`, or `scripts/maintenance/`.
- Code comments must be concise English comments; key script sections use numbered long `#` headings.
- Keep MySQL cleanup, ignore-rule cleanup, and archive registry changes in separate commits.

---

## File Map

- Modify: `apps/api/requirements.txt` - remove obsolete MySQL experiment dependencies.
- Delete: `apps/api/plantgenewiki_api/database/__init__.py` - remove unused MySQL package.
- Delete: `apps/api/plantgenewiki_api/database/config.py` - remove unused MySQL settings.
- Delete: `apps/api/tests/test_database_config.py` - remove obsolete MySQL configuration tests.
- Modify: `.gitignore` - remove stale `apps/agent` rules; explicitly ignore the root virtual environment and local archive mapping.
- Create: `config/archives.yaml` - tracked logical archive registry.
- Create locally but do not track: `config/archives.local.yaml` - server-specific logical-to-physical path mapping.
- Modify: `config/README.md` - document the two archive configuration files.
- Move outside repository: `data/meta/` and `data/pgcp_ortho/`.

### Task 1: Commit the existing MySQL experiment cleanup

**Files:**
- Modify: `apps/api/requirements.txt`
- Delete: `apps/api/plantgenewiki_api/database/__init__.py`
- Delete: `apps/api/plantgenewiki_api/database/config.py`
- Delete: `apps/api/tests/test_database_config.py`

**Interfaces:**
- Consumes: current dirty worktree containing only the four known MySQL cleanup paths.
- Produces: API dependency set containing only FastAPI and Uvicorn; no MySQL configuration package.

- [ ] **Step 1: Verify the cleanup diff is limited to the known files**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git status --short
git diff -- apps/api/requirements.txt apps/api/plantgenewiki_api/database apps/api/tests/test_database_config.py
```

Expected: exactly three deleted files and one modified requirements file; `requirements.txt` contains only `fastapi>=0.110.0` and `uvicorn[standard]>=0.27.0`.

- [ ] **Step 2: Verify no MySQL experiment references remain**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rg -n -i 'mysql|pymysql|sqlalchemy|alembic|DB_HOST|DB_PASSWORD' apps/api src tests scripts config || true
```

Expected: no output related to the removed MySQL experiment.

- [ ] **Step 3: Run the API test suite**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki/apps/api
../../.venv/bin/python -m unittest discover -s tests -v
```

Expected: four `SQLiteGraphStoreTest` tests pass.

- [ ] **Step 4: Commit only the MySQL cleanup**

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add apps/api/requirements.txt apps/api/plantgenewiki_api/database/__init__.py apps/api/plantgenewiki_api/database/config.py apps/api/tests/test_database_config.py
git commit -m "Remove obsolete MySQL experiment"
```

### Task 2: Clean ignored caches and stale ignore rules

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Consumes: ignored local build products and the current `.gitignore`.
- Produces: a smaller workspace and ignore rules matching the active project structure.

- [ ] **Step 1: Update `.gitignore`**

Replace the obsolete `# agent local runtime state` block with:

```gitignore
# local Python environment
.venv/

# local archive mapping
/config/archives.local.yaml
```

Keep the existing API secret, data, sequence, archive, frontend output, and editor rules unchanged.

- [ ] **Step 2: Check the ignore-rule diff**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git diff --check -- .gitignore
git diff -- .gitignore
```

Expected: stale `apps/agent` entries are removed; `.venv/` and `/config/archives.local.yaml` are added.

- [ ] **Step 3: Remove reproducible caches**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rm -rf apps/web/node_modules apps/web/dist apps/web/.astro
find . -type d -name __pycache__ -prune -exec rm -rf {} +
```

Expected: the listed cache directories no longer exist; tracked source files remain unchanged.

- [ ] **Step 4: Verify the root virtual environment remains ignored**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
test -x .venv/bin/python
git check-ignore .venv/ config/archives.local.yaml
git status --short
```

Expected: `.venv/bin/python` exists; both paths are ignored; only `.gitignore` and the already planned archive work may be dirty.

- [ ] **Step 5: Commit the ignore-rule cleanup**

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add .gitignore
git commit -m "Clean local runtime ignore rules"
```

### Task 3: Copy and verify large data archives

**Files:**
- Read: `data/meta/`
- Read: `data/pgcp_ortho/`
- Create outside Git: `/DATA/data2/plantgenewiki/archive/meta/`
- Create outside Git: `/DATA/data2/plantgenewiki/archive/pgcp_ortho/`
- Create outside Git: one `.plantgenewiki-manifest.sha256` per archive.

**Interfaces:**
- Consumes: ignored source trees under the repository `data/` directory.
- Produces: content-preserving archives with independently verifiable SHA-256 manifests.

- [ ] **Step 1: Record source counts and sizes**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
find data/meta -type f | wc -l
du -sb data/meta
find data/pgcp_ortho -type f | wc -l
du -sb data/pgcp_ortho
```

Expected: `data/meta` is approximately 5.6 GB with about 1,420 files; `data/pgcp_ortho` is approximately 26 GB with about 26,807 files. Stop if either directory is missing or unexpectedly empty.

- [ ] **Step 2: Create archive destinations**

Run:

```bash
mkdir -p /DATA/data2/plantgenewiki/archive/meta
mkdir -p /DATA/data2/plantgenewiki/archive/pgcp_ortho
```

Expected: both destination directories are writable by `nizhu`.

- [ ] **Step 3: Copy both trees with restart support**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rsync -aH --partial --info=progress2 data/meta/ /DATA/data2/plantgenewiki/archive/meta/
rsync -aH --partial --info=progress2 data/pgcp_ortho/ /DATA/data2/plantgenewiki/archive/pgcp_ortho/
```

Expected: both rsync commands exit with status `0`. If interrupted, rerun the same command.

- [ ] **Step 4: Verify metadata and file content before generating manifests**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rsync -aHnci --delete data/meta/ /DATA/data2/plantgenewiki/archive/meta/
rsync -aHnci --delete data/pgcp_ortho/ /DATA/data2/plantgenewiki/archive/pgcp_ortho/
```

Expected: no changed or missing file is listed. Any listed path blocks source deletion and requires rerunning Step 3.

- [ ] **Step 5: Generate source manifests and verify them at the destinations**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki/data/meta
find . -type f -print0 | sort -z | xargs -0 sha256sum > /DATA/data2/plantgenewiki/archive/meta/.plantgenewiki-manifest.sha256
cd /DATA/data2/plantgenewiki/archive/meta
sha256sum -c .plantgenewiki-manifest.sha256
cd /home/nizhu/Projects/PlantGeneWiki/data/pgcp_ortho
find . -type f -print0 | sort -z | xargs -0 sha256sum > /DATA/data2/plantgenewiki/archive/pgcp_ortho/.plantgenewiki-manifest.sha256
cd /DATA/data2/plantgenewiki/archive/pgcp_ortho
sha256sum -c .plantgenewiki-manifest.sha256
```

Expected: every entry reports `OK`; either command returning nonzero blocks source deletion.

### Task 4: Register verified archives without exposing server paths

**Files:**
- Create: `config/archives.yaml`
- Create locally: `config/archives.local.yaml`
- Modify: `config/README.md`

**Interfaces:**
- Consumes: verified archive directories and their SHA-256 manifests.
- Produces: a tracked logical registry and an ignored physical path map.

- [ ] **Step 1: Generate tracked and local archive configuration**

Run from the repository root:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
.venv/bin/python - <<'PY'
########## 0. imports ##########
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

########## 1. params ##########
archives = [
    ("meta-20260716", "metadata", "archive://plantgenewiki/meta", Path("/DATA/data2/plantgenewiki/archive/meta")),
    ("pgcp-ortho-20260716", "orthology", "archive://plantgenewiki/pgcp_ortho", Path("/DATA/data2/plantgenewiki/archive/pgcp_ortho")),
]

########## 2. registry ##########
records = []
for archive_id, category, archive_uri, archive_path in archives:
    manifest = archive_path / ".plantgenewiki-manifest.sha256"
    files = [path for path in archive_path.rglob("*") if path.is_file() and path != manifest]
    records.append(
        {
            "archive_id": archive_id,
            "category": category,
            "source_path": f"data/{archive_path.name}",
            "archive_path": archive_uri,
            "source_or_batch": "legacy_project_data",
            "version": "2026-07-16",
            "file_count": len(files),
            "size_bytes": sum(path.stat().st_size for path in files),
            "checksum_manifest": f"sha256:{sha256(manifest.read_bytes()).hexdigest()}",
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "status": "verified",
        }
    )

lines = ["archives:"]
for record in records:
    lines.append(f"  - archive_id: {record['archive_id']}")
    for key in (
        "category",
        "source_path",
        "archive_path",
        "source_or_batch",
        "version",
        "file_count",
        "size_bytes",
        "checksum_manifest",
        "archived_at",
        "status",
    ):
        lines.append(f"    {key}: {record[key]}")
Path("config/archives.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")

########## 3. local mapping ##########
local_lines = ["archive_paths:"]
for _, _, archive_uri, archive_path in archives:
    local_lines.append(f"  {archive_uri}: {archive_path}")
Path("config/archives.local.yaml").write_text("\n".join(local_lines) + "\n", encoding="utf-8")
PY
```

Expected: `config/archives.yaml` contains logical `archive://` addresses and measured values; only `config/archives.local.yaml` contains `/DATA/...` paths.

- [ ] **Step 2: Document archive configuration**

Append this section to `config/README.md`:

```markdown
## Archive registry

`archives.yaml` tracks logical archive identifiers, provenance, counts, sizes, and checksum manifests. It is safe to commit because it does not contain machine-specific paths.

`archives.local.yaml` maps logical archive addresses to physical storage paths on one machine. It is local-only and must not be committed.
```

- [ ] **Step 3: Verify the registry and path separation**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rg -n '/DATA/|/home/nizhu' config/archives.yaml config/README.md && exit 1 || true
rg -n '/DATA/data2/plantgenewiki/archive' config/archives.local.yaml
git check-ignore config/archives.local.yaml
git diff --check -- config/archives.yaml config/README.md
```

Expected: tracked files contain no internal path; the local file contains both mappings and is ignored.

- [ ] **Step 4: Commit the archive registry**

```bash
cd /home/nizhu/Projects/PlantGeneWiki
git add config/archives.yaml config/README.md
git commit -m "Register verified data archives"
```

### Task 5: Remove verified source copies and run final validation

**Files:**
- Delete outside Git tracking: `data/meta/`
- Delete outside Git tracking: `data/pgcp_ortho/`

**Interfaces:**
- Consumes: archives with verified manifests and committed registry records.
- Produces: a smaller repository workspace with recoverable external archives.

- [ ] **Step 1: Recheck archive manifests immediately before deletion**

Run:

```bash
cd /DATA/data2/plantgenewiki/archive/meta
sha256sum -c .plantgenewiki-manifest.sha256
cd /DATA/data2/plantgenewiki/archive/pgcp_ortho
sha256sum -c .plantgenewiki-manifest.sha256
```

Expected: all entries report `OK`. Stop on the first failure.

- [ ] **Step 2: Remove only the two verified source directories**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rm -rf -- data/meta data/pgcp_ortho
```

Expected: both source directories are absent; archive destinations remain present.

- [ ] **Step 3: Reinstall frontend dependencies and verify the application**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki/apps/web
npm ci
npm run check
npm run build
cd /home/nizhu/Projects/PlantGeneWiki/apps/api
../../.venv/bin/python -m unittest discover -s tests -v
```

Expected: Astro check and build succeed; all four API tests pass.

- [ ] **Step 4: Remove regenerated frontend caches and inspect final state**

Run:

```bash
cd /home/nizhu/Projects/PlantGeneWiki
rm -rf apps/web/node_modules apps/web/dist apps/web/.astro
du -sh . data /DATA/data2/plantgenewiki/archive/meta /DATA/data2/plantgenewiki/archive/pgcp_ortho
git status --short
git log -4 --oneline
```

Expected: the repository is substantially smaller; data archives remain external; no unexpected tracked changes are present; the three cleanup commits are visible.
