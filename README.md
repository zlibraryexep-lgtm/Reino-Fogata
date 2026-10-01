# Calendario Medieval 2026–2030
Sitio estático para GitHub Pages: `index.html` + `news.json` (se renueva solo cada día).

Archivos: `index.html`, `news.json`, `scripts/noticias.py`, `.github/workflows/noticias.yml`.

1. Settings → Pages → Deploy from a branch → main / (root).
2. Settings → Actions → General → Workflow permissions → "Read and write permissions".
3. Actions → "Noticias diarias" → Run workflow (para probar). Revisa el log: dice qué fuentes respondieron.
4. Opcional: en Settings → Secrets → Actions agrega `ANTHROPIC_API_KEY` para traducir las noticias al español.
