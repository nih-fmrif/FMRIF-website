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
