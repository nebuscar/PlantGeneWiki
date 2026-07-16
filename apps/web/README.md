# PhytoAtlas Web

Vue 3 application for the interactive PhytoAtlas knowledge platform.

## Runtime boundary

The frontend reads normalized knowledge objects only through the FastAPI service. It must not read raw FASTA, GFF, source JSON, PDFs, internal server paths, or generated static API files.

Configure the API base URL in `.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Local development

Start the API from `apps/api`:

```bash
uvicorn phytoatlas_api.main:app --reload --host 0.0.0.0 --port 8000
```

Start the web application from `apps/web`:

```bash
npm install
npm run dev
```

The default development URL is `http://localhost:4322`.

## Verify

```bash
npm test
npm run build
```

## Cloudflare

Use `apps/web` as the build root.

- Build command: `npm run build`
- Output directory: `dist`
- Framework preset: Vue
- SPA fallback: `public/_redirects`
