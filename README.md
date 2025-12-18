# Grobid-footnote-flavour

This repo contains training data and other resources for building a [Grobid](https://github.com/kermitt2/grobid) flavour that can deal with references in footnotes, which is a common practice in law and the humanities.

This project is a collaboration between Christian Boulanger ([mpilhlt](https://www.lhlt.mpg.de/boulanger#)) and Luca Foppiano ([ScienciaLAB](https://sciencialab.com/)).

## Data Structure

The structure of the data will be based on batches and will follow this structure:

```
├── batches
│   └── batch_1
│       ├── 0_input
│       │   ├── 10.12946__rg01__036-055.pdf
│       │   └── 10.5771__2699-1284-2020-1-16.pdf
│       ├── 1_generated
│       └── 2_corrected
```



