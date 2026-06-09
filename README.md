# Grobid-footnote-flavour

This repo contains training data and other resources for building a [Grobid](https://github.com/kermitt2/grobid) flavour that can deal with references in footnotes, which is a common practice in law and the humanities.

This project is a collaboration between Christian Boulanger ([mpilhlt](https://www.lhlt.mpg.de/boulanger#)) and Luca Foppiano ([ScienciaLAB](https://sciencialab.com/)).

## Schemas

Standalone RNG schemas for validating GROBID training files are published at:

**<https://mpilhlt.github.io/grobid-footnote-flavour/schema>**

| Schema | Validates |
| ------ | --------- |
| [grobid.training.segmentation.rng](https://mpilhlt.github.io/grobid-footnote-flavour/schema/grobid.training.segmentation.rng) | `*.training.segmentation.tei.xml` |
| [grobid.training.references.rng](https://mpilhlt.github.io/grobid-footnote-flavour/schema/grobid.training.references.rng) | `*.training.references.tei.xml` |
| [grobid.training.references.referenceSegmenter.rng](https://mpilhlt.github.io/grobid-footnote-flavour/schema/grobid.training.references.referenceSegmenter.rng) | `*.training.references.referenceSegmenter.tei.xml` |

### Schema authoring

The schemas in `docs/schema/` are **auto-generated** and must not be edited directly. The composable source lives in `schema/`:

```text
schema/
  shared/
    tei-header.rng        # shared TEI header elements
    bibl-struct.rng       # shared biblStruct elements
    common-elements.rng   # lb, ptr, ref, label
  grobid.training.references.rng
  grobid.training.references.referenceSegmenter.rng
  grobid.training.segmentation.rng
```

After editing any file under `schema/`, regenerate and commit the flattened schemas:

```bash
uv sync --group dev        # first time only
uv run python scripts/build-schema.py
git add docs/schema/
git commit -m "Regenerate schemas"
```

The build script will abort with an error if any `<define>` name appears more than once in a flattened output — a sign that a shared element needs a filename-stem prefix (e.g. `bibl-struct_note` instead of `note`).

## Data Structure

The structure of the data will be based on batches and will follow this structure:

```text
├── batches
│   └── batch_1
│       ├── 0_input
│       │   ├── 10.12946__rg01__036-055.pdf
│       │   └── 10.5771__2699-1284-2020-1-16.pdf
│       ├── 1_generated
│       └── 2_corrected
```



