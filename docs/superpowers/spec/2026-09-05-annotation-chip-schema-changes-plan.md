# Implementation plan: schema annotations for pdf-tei-editor's chip redesign

## Context

`pdf-tei-editor` (a downstream consumer of this repo's published schemas at
`https://mpilhlt.github.io/grobid-footnote-flavour/schema/`) currently
hand-maintains a duplicate, drifting copy of this schema's tag/attribute
descriptions and a curated subset of attribute values, used to render
annotation "chips" (buttons) in its visual XML editor. It's redesigning
that system to generate the chip UI directly from these RNG schemas
instead, using two mechanisms RelaxNG already supports:

1. **`<a:documentation>` annotations** (the standard RelaxNG Compatibility
   Annotations namespace) on `<element>`, `<attribute>`, and `<value>`
   nodes — used as hover-tooltip text for the corresponding chip/menu item.
   This repo already has precedent for this: `docs/schema/TEI-biblStruct.rng`
   (well, more precisely — see "Convention" below for the exact form to use).
2. **Enumerated `<value>` lists** inside `<attribute>` — used to build a
   dropdown of variants under a chip. Several attributes currently used by
   the training data are *not* enumerated at all in this schema (freeform
   `<attribute name="...">` with no `<choice>`), which loses curated
   attribute-value presets pdf-tei-editor's current manual config provides.
   This plan adds real enumerations for those, grounded in what's actually
   used in `batches/**/*.tei.xml` today (checked below) so nothing already
   valid becomes invalid.

None of this changes GROBID training/inference behavior — `<a:documentation>`
is inert to any RNG validator, and every enum widening/local-override below
was checked against the actual training corpus to confirm it doesn't
narrow what's currently accepted.

## Goals

- Add `<a:documentation>` to every element/attribute/value listed in the
  migration table below, across all three schemas.
- Add real `<choice>` enumerations for four attributes that are currently
  freeform, via **references-local override defines** (not edits to the
  shared defines they'd otherwise come from), so unrelated contexts
  (`teiHeader`, `biblStruct` in `shared/bibl-struct.rng`) are unaffected.
- Widen three already-partially-enumerated attributes with missing values.
- Regenerate `docs/schema/*.rng` and confirm the existing training corpus
  in `batches/` still validates.

## Non-goals

- No change to GROBID's actual training/inference model or feature
  extraction.
- No change to `docs/schema/Grobid.rng` / `docs/schema/Grobid.odd` (the
  full GROBID master schema) — those aren't generated from `schema/` by
  `scripts/build-schema.py` and are out of scope here.
- No change to `schema/xsd/` (unrelated to this repo's own build; that
  directory doesn't exist here — ignore if you don't find it).
- No decision here on whether `title@level="u"` (unpublished) or the
  `div@type` values not yet used in real data (`funding`, `conflict`,
  `contribution`, `availability`) should be trimmed from the schema —
  they're kept as-is; this plan only adds documentation to them.

## Convention: `<a:documentation>`

Declare the annotations namespace once on each file's root `<grammar>`
element you touch, rather than repeating it on every node:

```xml
<grammar xmlns="http://relaxng.org/ns/structure/1.0"
  xmlns:xml="http://www.w3.org/XML/1998/namespace"
  xmlns:a="http://relaxng.org/ns/compatibility/annotations/1.0"
  ns="http://www.tei-c.org/ns/1.0">
```

Then:

- **Element-level** (tag description — shown on the chip itself): first
  child of the `<element>`, before any `<attribute>`/`<optional>`/etc.

  ```xml
  <define name="references_citedRange">
    <element name="citedRange">
      <a:documentation>Pinpoint into a statute or decision (section,
        subsection, marginal number, etc.)</a:documentation>
      <attribute name="unit">
        ...
  ```

- **Attribute-level** (fallback description when a specific value doesn't
  have its own): first child of the `<attribute>`.
- **Value-level** (per-variant description, e.g. distinguishing
  `citedRange[unit=page]` from `citedRange[unit=section]`): **NOT** a
  direct child of `<value>` — `<value>` (like `<name>`/`<param>`) has a
  text-only content model in RelaxNG and rejects foreign-namespace
  children (confirmed with both `jing -s` and `lxml.etree.RelaxNG`; an
  earlier draft of this plan incorrectly claimed the opposite). Instead,
  wrap the `<value>` in a `<group>` and put the `<a:documentation>` as
  the group's first child. A `<group>` containing exactly one pattern is
  semantically identical to that pattern alone, so this doesn't change
  what validates:

  ```xml
  <group>
    <a:documentation>Pinpoint by printed page number</a:documentation>
    <value>page</value>
  </group>
  ```

  This is the same pattern already used below for `references_title`'s
  level/type combos (there, groups with 1-2 attributes) — apply it to
  every other value-level annotation in this plan too, including inside
  the `references_idno`, `references_biblScope`, and `references_note`
  code blocks in Task 1/2 below, which still show the old (invalid)
  child-of-`<value>` form as originally drafted.

Files that need the `xmlns:a` declaration added: `schema/grobid.training.references.rng`,
`schema/grobid.training.references.referenceSegmenter.rng`,
`schema/grobid.training.segmentation.rng`, `schema/shared/bibl-struct.rng`,
`schema/shared/common-elements.rng` (only if you add docs to `label`/`ref`/`ptr`/`lb` there — the
migration table below doesn't require it, so this file can likely be skipped).

## Task 1 — `references_title`, `references_idno`, `references_biblScope` local overrides

In `schema/grobid.training.references.rng`, `title`, `idno`, and
`biblScope` are currently referenced from the shared
`schema/shared/bibl-struct.rng` defines. Those shared defines are also
used by `teiHeader/titleStmt`, `editionStmt/edition`, and
`biblStruct`'s `analytic`/`monogr`/`series` (in all three schemas, via the
shared include) — enumerating or requiring their attributes there would
narrow validity for those unrelated contexts (a real bibliography's
`idno@type="ISBN"`, a document title with no level in `titleStmt`, etc.).

This repo already solves this exact problem for `date` and `citedRange` —
see the existing `references_date` and `references_citedRange` local
overrides in `schema/grobid.training.references.rng` (with comments
explaining exactly this rationale). Follow the same pattern for these
three.

**Corpus check performed** (so these choices don't break existing data):

```bash
grep -rhoE '<idno[^>]*type="[^"]*"' batches --include="*.training.references.tei.xml" | sort -u
#   -> type="ISSN"   (only this one; not in the legal-citation list — included below)
grep -rhoE '<biblScope[^>]*unit="[^"]*"' batches --include="*.training.references.tei.xml" | sort -u
#   -> unit="issue", unit="page", unit="volume"
grep -rhoE '<title[^>]*level="[^"]*"' batches --include="*.training.references.tei.xml" | sort -u
#   -> level="a", level="j", level="m", level="s"   (no bare <title> without a level found anywhere)
grep -rhoE '<title[^>]*type="[^"]*"' batches --include="*.training.references.tei.xml" | sort -u
#   -> (no results — type=legislation/caseName aren't in any existing training file yet)
```

Add to `schema/grobid.training.references.rng` (near the other
`references_*` local overrides, e.g. after `references_edition`):

```xml
<!-- references_idno: local override of the shared bib-struct <idno>,
     scoped to this flat <bibl> content model, so a curated identifier
     type list doesn't leak into teiHeader/biblStruct idno usage
     elsewhere. Includes ISSN (in use in existing training data) alongside
     the legal-citation identifier types from #41. -->
<define name="references_idno">
  <element name="idno">
    <a:documentation>Document or serial identifier.</a:documentation>
    <optional>
      <attribute name="type">
        <choice>
          <value>DOI<a:documentation>Digital Object Identifier</a:documentation></value>
          <value>ISSN<a:documentation>Serial (journal) identifier</a:documentation></value>
          <value>arXiv<a:documentation>arXiv preprint identifier</a:documentation></value>
          <value>report<a:documentation>Technical/institutional report number</a:documentation></value>
          <value>docket<a:documentation>Court docket number</a:documentation></value>
          <value>ECLI<a:documentation>European Case Law Identifier</a:documentation></value>
          <value>CELEX<a:documentation>EU CELEX document identifier</a:documentation></value>
        </choice>
      </attribute>
    </optional>
    <text/>
  </element>
</define>

<!-- references_biblScope: local override of the shared bib-struct
     <biblScope>, scoped to this flat <bibl> content model. -->
<define name="references_biblScope">
  <element name="biblScope">
    <a:documentation>Volume/issue/page extent of the containing work.</a:documentation>
    <optional>
      <attribute name="unit">
        <choice>
          <value>page<a:documentation>Full page range of the article</a:documentation></value>
          <value>volume<a:documentation>Volume number</a:documentation></value>
          <value>issue<a:documentation>Issue / number</a:documentation></value>
        </choice>
      </attribute>
    </optional>
    <optional>
      <attribute name="from"/>
    </optional>
    <optional>
      <attribute name="to"/>
    </optional>
    <text/>
  </element>
</define>

<!-- references_title: local override of the shared bib-struct <title>,
     scoped to this flat <bibl> content model. Unlike the shared title
     (used by teiHeader/titleStmt and biblStruct, where a title's level
     is legitimately unset), a title inside a flat bibliographic
     reference always classifies as one of the presets below, so —
     unlike the shared define — this one is not left with two
     independent optional attributes: level+type are grouped into named
     presets, since "type=legislation" only ever co-occurs with
     "level=m", never independently. -->
<define name="references_title">
  <element name="title">
    <a:documentation>Title of the cited work.</a:documentation>
    <optional>
      <attribute name="key">
        <a:documentation>Short resolvable key for a named work, e.g. a
          statute abbreviation (key="UrhG"), so it can later be linked to
          an external norm/case database.</a:documentation>
      </attribute>
    </optional>
    <choice>
      <group>
        <a:documentation>Article or chapter title (analytics)</a:documentation>
        <attribute name="level"><value>a</value></attribute>
      </group>
      <group>
        <a:documentation>Journal title</a:documentation>
        <attribute name="level"><value>j</value></attribute>
      </group>
      <group>
        <a:documentation>Monograph, proceedings, book, or thesis title</a:documentation>
        <attribute name="level"><value>m</value></attribute>
      </group>
      <group>
        <a:documentation>Series title</a:documentation>
        <attribute name="level"><value>s</value></attribute>
      </group>
      <group>
        <a:documentation>Unpublished work title</a:documentation>
        <attribute name="level"><value>u</value></attribute>
      </group>
      <group>
        <a:documentation>Title of a statute / legislative act</a:documentation>
        <attribute name="level"><value>m</value></attribute>
        <attribute name="type"><value>legislation</value></attribute>
      </group>
      <group>
        <a:documentation>Case name of a court ruling</a:documentation>
        <attribute name="level"><value>a</value></attribute>
        <attribute name="type"><value>caseName</value></attribute>
      </group>
    </choice>
    <text/>
  </element>
</define>
```

Then change `bibl`'s content model in the same file (currently a
`<zeroOrMore><choice>` listing `<ref name="title"/>`,
`<ref name="biblScope"/>`, `<ref name="idno"/>` among others) to point at
the new local names instead: `references_title`, `references_biblScope`,
`references_idno`. Leave every other `<ref>` in that choice unchanged.

## Task 2 — widen already-partially-enumerated attributes (direct edits)

These defines are already local to one file (not shared), so no override
indirection is needed — edit them in place.

**`schema/grobid.training.references.rng`**, `references_ptr` — add `web`
as the enumerated (currently freeform) type, plus element/value docs:

```xml
<define name="references_ptr">
  <element name="ptr">
    <a:documentation>Web URL (exclude prefixes like 'URL:' and trailing periods).</a:documentation>
    <optional>
      <attribute name="type">
        <choice>
          <value>web</value>
        </choice>
      </attribute>
    </optional>
    <optional>
      <attribute name="target"/>
    </optional>
    <text/>
  </element>
</define>
```

**`schema/grobid.training.references.rng`**, `references_note` — add
`report` as the enumerated (currently freeform) type:

```xml
<define name="references_note">
  <element name="note">
    <a:documentation>Any note not covered by another tag.</a:documentation>
    <optional>
      <attribute name="type">
        <choice>
          <value>report<a:documentation>Type of report or thesis (e.g. 'Ph.D. thesis', 'Technical Report')</a:documentation></value>
        </choice>
      </attribute>
    </optional>
    <text/>
  </element>
</define>
```

**`schema/grobid.training.segmentation.rng`**, `div` — add `contribution`
to the existing 6-value `type` enum (`toc`, `acknowledgement`,
`availability`, `funding`, `annex`, `conflict`):

```xml
<attribute name="type">
  <choice>
    <value>toc</value>
    <value>acknowledgement</value>
    <value>availability</value>
    <value>funding</value>
    <value>annex</value>
    <value>conflict</value>
    <value>contribution</value>
  </choice>
</attribute>
```

⚠️ **Data note found while checking the corpus** — worth a decision before
or alongside this edit, not strictly required by it:

```bash
grep -rhoE '<div[^>]*type="[^"]*"' batches --include="*.training.segmentation.tei.xml" | sort -u
#   -> type="acknowledgement", type="acknowledgment", type="annex", type="toc"
```

One existing file
(`batches/batch_2/4_packaging/segmentation/tei/10.12759__hsr.6.1981.3.3-17.training.segmentation.tei.xml`)
uses the American spelling `type="acknowledgment"`, which the schema does
not and will not enumerate (only the British `acknowledgement`). This
file is presumably already failing strict validation against the current
schema, independent of this change. Recommend fixing the training file to
the British spelling to match the schema, rather than adding a second
spelling to the enum — but flagging for a decision rather than silently
changing training data as a side effect of this schema task.

**`schema/grobid.training.references.referenceSegmenter.rng`**, `bibl` —
add `decision`/`legislation` to match the (already enumerated) `bibl@type`
in `grobid.training.references.rng`:

```xml
<define name="bibl">
  <element name="bibl">
    <optional>
      <attribute name="type">
        <choice>
          <value>footnote<a:documentation>A note or comment that is not a bibliographic reference</a:documentation></value>
          <value>decision<a:documentation>A court ruling / judicial decision citation</a:documentation></value>
          <value>legislation<a:documentation>A statute / legislation citation</a:documentation></value>
        </choice>
      </attribute>
    </optional>
    ...
```

(No training file currently sets `bibl@type` at all in this variant per
the corpus check, so this is a pure widening with zero compatibility
risk.)

## Task 3 — remaining `<a:documentation>` (no structural change)

Add element/attribute/value-level `<a:documentation>` per the table below.
Every row not covered by Tasks 1–2 above needs only a documentation
addition, no `<choice>`/structural change.

### `schema/grobid.training.segmentation.rng`

| Element (`define`) | Attribute=Value | Documentation text |
| --- | --- | --- |
| `body` | — | The main body of the document |
| `listBibl` | — | Bibliographical section |
| `front` | — | Document header / front matter |
| `titlePage` | — | Cover page |
| `segmentation_note`, value `footnote` | place=footnote | Page footer or numbered footnote |
| `page` | — | Page number indicator |
| `div`, value `acknowledgement` | type=acknowledgement | Acknowledgement statement in the annex |
| `div`, value `toc` | type=toc | Table of contents |
| `segmentation_note`, value `headnote` | place=headnote | Page header / running head |
| `div`, value `annex` | type=annex | Any other annex section |
| `div`, value `funding` | type=funding | Funding information annex |
| `div`, value `conflict` | type=conflict | Conflict of interest statement |
| `div`, value `contribution` | type=contribution | Author contribution statement |
| `div`, value `availability` | type=availability | Data/code availability statement |

### `schema/grobid.training.references.referenceSegmenter.rng`

| Element (`define`) | Attribute=Value | Documentation text |
| --- | --- | --- |
| `bibl` (element-level, bare case) | — | An individual bibliographic reference |
| `bibl`, value `footnote` | type=footnote | A note or comment that is not a bibliographic reference |
| `label` | — | Reference number or footnote marker (e.g. [1], ¹) |
| `bibl`, value `decision` | type=decision | A court ruling / judicial decision citation |
| `bibl`, value `legislation` | type=legislation | A statute / legislation citation |

### `schema/grobid.training.references.rng`

| Element (`define`) | Attribute=Value | Documentation text |
| --- | --- | --- |
| `bibl` (element-level, bare case) | — | An individual bibliographic reference |
| `bibl`, value `footnote` | type=footnote | A note or comment that is not a bibliographic reference |
| `bibl`, value `decision` | type=decision | A court ruling / judicial decision citation |
| `bibl`, value `legislation` | type=legislation | A statute / legislation citation |
| `orgName`, value `court` | type=court | Court issuing a decision |
| `orgName` (element-level) | — | Institution for theses or technical reports |
| `orgName`, value `collaboration` | type=collaboration | Project-based collaboration acting as an author group |
| `references_citedRange` (element-level) | — | Pinpoint into a statute or decision (section, subsection, marginal number, etc.) |
| `references_citedRange`, value `section` | unit=section | Numbered section, e.g. § 19a |
| `references_citedRange`, value `sub-section` | unit=sub-section | Subsection, e.g. Abs. 2 |
| `references_citedRange`, value `sentence` | unit=sentence | Sentence within a subsection, e.g. Satz 2 |
| `references_citedRange`, value `number` | unit=number | Numbered item, e.g. Nr. 3 |
| `references_citedRange`, value `letter` | unit=letter | Lettered item, e.g. lit. b |
| `references_citedRange`, value `margin` | unit=margin | Marginal number, e.g. Rn./Tz. 12 |
| `references_citedRange`, value `recital` | unit=recital | Recital of an EU legal act |
| `references_citedRange`, value `page` | unit=page | Pinpoint by printed page number |
| `references_seg`, value `signal` | type=signal | Discourse signal word introducing or framing a citation (e.g. 'see', 'vgl.', 'cf.') |
| `author` | — | Complete sequence of author names |
| `references_date` (element-level) | — | Publication date sequence |
| `references_date`, value `decision` | type=decision | Date a court decision was issued |
| `references_date`, value `enacted` | type=enacted | Date a statute was enacted |
| `references_date`, value `publication` | type=publication | Date of publication |
| `publisher` | — | Publisher name; also used for corporate authors such as web pages |
| `references_edition` | — | Edition of a publication |
| `pubPlace` | — | Publication place or location of publishing institution |
| `editor` | — | Sequence of editor names |
| `references_ref`, value `anaphoric` | type=anaphoric | Points backward, e.g. "ibid.", "id.", "op. cit.", "supra note 5" |
| `references_ref`, value `cataphoric` | type=cataphoric | Points forward, e.g. "infra", "see note 12 below" |

`references_title`, `references_idno`, `references_biblScope`,
`references_ptr`, and `references_note` already get their documentation
inline as part of Task 1/2's XML blocks above — don't duplicate them here.

## Build & validate

```bash
uv sync --group dev   # first time only
uv run python scripts/build-schema.py
```

The script aborts on duplicate `<define>` names across an included set —
if it complains about `title`/`idno`/`biblScope` colliding, it means
`references_title`/`references_idno`/`references_biblScope` weren't named
distinctly from the shared ones, or a `<ref>` in `bibl`'s content model
still points at the old shared name instead of the new local one.

After a successful build, validate the existing training corpus against
the regenerated schema to confirm nothing broke (adjust to whatever
validator this repo's CI already uses — `jing` if on `PATH`, per the
build script's own optional check):

```bash
for f in batches/**/*.training.references.tei.xml; do
  jing docs/schema/grobid.training.references.rng "$f" || echo "FAILED: $f"
done
for f in batches/**/*.training.references.referenceSegmenter.tei.xml; do
  jing docs/schema/grobid.training.references.referenceSegmenter.rng "$f" || echo "FAILED: $f"
done
for f in batches/**/*.training.segmentation.tei.xml; do
  jing docs/schema/grobid.training.segmentation.rng "$f" || echo "FAILED: $f"
done
```

The one known pre-existing expected failure is the `acknowledgment`
(American spelling) file flagged in Task 2 — everything else should pass
both before your changes (baseline) and after.

## Definition of done

- [ ] `xmlns:a` declared on the grammars touched.
- [ ] `references_title`, `references_idno`, `references_biblScope` added
      to `schema/grobid.training.references.rng`; `bibl`'s content model
      updated to reference them instead of the shared defines.
- [ ] `references_ptr@type`, `references_note@type` enumerated.
- [ ] `div@type` gains `contribution`; `referenceSegmenter`'s `bibl@type`
      gains `decision`/`legislation`.
- [ ] Every row in the Task 3 table has a corresponding `<a:documentation>`
      in the source `.rng`.
- [ ] `uv run python scripts/build-schema.py` runs clean, `docs/schema/*.rng`
      regenerated and committed.
- [ ] Corpus validation shows no new failures beyond the pre-existing
      `acknowledgment` file (or that file has been fixed too, if you
      decide to address it).
- [ ] `git commit` per this repo's own convention (`git commit -m "Regenerate schemas"`
      after `docs/schema/` changes, per `README.md`), and pushed so the
      published schema at `https://mpilhlt.github.io/grobid-footnote-flavour/schema/`
      picks it up.
