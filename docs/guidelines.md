# Annotation guidelines 

This document complements what's described in the related model in the grobid documentation.

## Segmentation 

We introduce a new label called `<toc>` which is used to mark the table of contents in the document, when present.
For the moment, the block within the `<toc>` tag is ignored until enough training data is available. 

### References / Footnotes
In this flavour referenecs are mixed with footnotes with three different styles: 
1. pure footnote with a comment related to a content in the text, annotated as `<note place="footnote">.....</note>`
2. pure reference, with the data of the referred article, annotated as `<listBibl>....</listBibl>` 
3. mixed content, with a comment related to the body and a reference annexed to it, annotated as `<listBibl>....</listBibl>` 



