# Config

Public configuration templates and mappings belong here.

Do not commit private credentials or machine-specific secrets.

## Archive registry

`archives.yaml` tracks logical archive identifiers, provenance, counts, sizes, and checksum manifests. It is safe to commit because it does not contain machine-specific paths.

`archives.local.yaml` maps logical archive addresses to physical storage paths on one machine. It is local-only and must not be committed.
