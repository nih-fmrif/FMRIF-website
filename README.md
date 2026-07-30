# FMRIF Website

Pelican static-site scaffold for the Functional MRI Facility website.

## Local development

Install the Python dependencies, then build or serve the site:

```bash
python -m pip install -r requirements.txt
make build
make serve
```

## Content model

- `content/facilities/` contains facility pages.
- `content/staff/` contains staff profile pages.
- `content/summer-course/` contains FMRIF Summer Course pages.
- `content/pages/` contains fixed landing pages and operational link targets.
- `content/assets/` and `content/images/` contain static files copied into the site.

The main navigation is configured in `pelicanconf.py`.

## Deployment

The default production target is the NIH hostname:

```bash
make publish
```

`publishconf.py` defaults to `https://fmrif.nimh.nih.gov`. To test another
absolute URL locally, override `SITEURL`:

```bash
SITEURL=https://example.org make publish
```

GitHub Pages is the special case. Pushes to `main` use
`.github/workflows/pelican.yml`, which computes the GitHub Pages URL and passes
it into `publishconf.py`. For a manual Actions run, you can override `SITEURL`
with an absolute URL such as:

```text
https://fmrif.nimh.nih.gov
```

Large PDF assets are intentionally ignored at `content/pdf/`; host those outside
the git repository and keep the lecture metadata links pointed at their deployed
URLs.
