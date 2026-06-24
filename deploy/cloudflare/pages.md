# Cloudflare Pages Deployment

PlantGeneWiki Web is designed for Cloudflare Pages as a static-first knowledge-base frontend.

## Pages Settings

- Project root directory: `apps/web`
- Framework preset: `Astro`
- Build command: `npm run build`
- Build output directory: `dist`
- Node version: `20`

## Data Boundary

Cloudflare Pages serves published website data only:

```text
apps/web/public/data/api/
```

Do not publish raw FASTA, GFF, PGCP raw JSON dumps, PDFs, vector stores, SQLite databases, or internal server paths through Pages.

Large public artifacts can later be synchronized to Cloudflare R2. Internal raw data should stay on the lab server and be represented on the website through Dataset records.

## Future Dynamic Migration

The current static paths intentionally mirror future API routes:

```text
/data/api/genes/<id>.json      -> /api/genes/<id>
/data/api/species/<id>.json    -> /api/species/<id>
/data/api/datasets/<id>.json   -> /api/datasets/<id>
/data/api/search/index.json    -> /api/search
/data/api/graph/*.json         -> /api/graph
```

When Workers or another API layer is added, keep the response shape stable so frontend pages do not need to be rewritten.
