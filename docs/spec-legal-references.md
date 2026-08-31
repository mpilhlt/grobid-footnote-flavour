# Specification: Labeling references to laws and court rulings

| | |
| --- | --- |
| **Status** | Draft / proposal — decisions open (see §5) |
| **Issue** | [mpilhlt/grobid-footnote-flavour#41](https://github.com/mpilhlt/grobid-footnote-flavour/issues/41) |
| **Affects** | `schema/grobid.training.references.rng`, `schema/grobid.training.references.referenceSegmenter.rng`, `schema/shared/bibl-struct.rng`, `docs/guidelines.md`, downstream TEI mapping |
| **Sample source** | Duranteye (2020), `10.5771/2699-1284-2020-1-16` |

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used as in RFC 2119.

This document is written as a set of **decisions with options** (§5). Each option is
scored against existing standards so that we adopt established vocabulary wherever one
exists and only invent tokens where none does. §6 collects the recommended option from each
decision into a single profile with schema patches and examples.

---

## 1. Motivation

German legal footnotes cite two reference genres that the current flavour cannot represent
without loss or mislabeling:

1. **Statutory / norm references** such as `§ 19a Abs. 2 UrhG` — no label identifies `UrhG`
   as a norm, and section (`§ 19a`) / subsection (`Abs. 2`) are not distinguished from one
   another or from page numbers.
2. **Court rulings** such as `EuGH, Urt. v. 8.9.2016 – C-160/15, GRUR 2016, 1152 Tz. 24 –
   GS Media/Sanoma`, currently mislabeled:

   | Fragment | Current label | Problem |
   | --- | --- | --- |
   | `Tz. 24` (marginal number) | `<biblScope unit="page">` | A *Randnummer* is not pagination. Misleading when the decision has no pages, or when pages come from the journal version (`GRUR`). |
   | `GS Media/Sanoma` (case short-name) | *starts a new `<bibl>`* | The `– Party/Party` tail belongs to the reference; the referenceSegmenter must not split on it. |
   | `EuGH` (court) | `<author>` | A court is an institution, not a person. |
   | `C-160/15` (docket) | `<title>` | A docket number is an identifier, not a title. |

## 2. Goals and non-goals

**Goals**

- TEI P5–compliant target markup for statutory and court-ruling references in
  `*.training.references.tei.xml` and `*.training.references.referenceSegmenter.tei.xml`.
- Reuse of existing standard vocabulary (TEI, CSL, ECLI) wherever it fits.
- Keep markup inside GROBID's flat-`<bibl>` training style (no nested `<biblStruct>`).
- Distinguish *pinpoint* citations (section, subsection, marginal number) from the
  *extent* of the container work (reporter volume, year, first page).

**Non-goals**

- Resolving citations to external norm/case databases (only an optional `@key` / `@ref`
  hook is provided).
- Changing the `grobid.training.segmentation` (page-level) model.
- Full document markup of the cited norms/judgments themselves (that is Akoma Ntoso's job;
  see §3.5).

---

## 3. Prior art — what not to reinvent

Neither FOSSIL / this GROBID specialization nor any surveyed standard already provides a
ready-made tagset for legal citation strings in footnotes — that is the gap this spec
fills. What the standards below *do* provide is reusable **element and value vocabulary**,
which we adopt instead of coining our own wherever one fits.

### 3.1 GROBID native citation tagset

GROBID's citation and referenceSegmenter models emit a **flat** `<bibl>` with a fixed label
inventory: `<author>`, `<title level="a|j|m|s|u">`, `<editor>`, `<date>`,
`<biblScope unit="volume|issue|page">`, `<pubPlace>`, `<publisher>`, `<idno type="…">`,
`<ptr type="web">`, `<note>`, `<label>`. It has **no** legal-specific label. Whatever we
choose, the model must learn it as one of these labels (or a new one we add to the
flavour), and any richer structure is produced by post-processing. This repo already
extends the set with `<seg type="signal">`, repurposed `<ref type="anaphoric|cataphoric">`,
`<orgName type>`, `<edition>`, and `<bibl type="footnote">`.

### 3.2 TEI P5 core

- **`<bibl>` `@type`** — from `att.typed`; datatype `data.enumerated`, i.e. "values are
  locally defined by each project." TEI publishes **no** value list for `bibl/@type`
  (`type="book"` etc. in the Guidelines are examples, not a taxonomy).
- **`<biblScope>` vs `<citedRange>`** — both are in `att.citing` (`@unit`, `@from`, `@to`,
  `@n`) and both are valid directly in `<bibl>`. The Guidelines distinguish them by
  meaning: `<biblScope>` "defines the scope of a bibliographic reference, for example a
  list of page numbers, or a named subdivision of a larger work" (the item's own extent);
  `<citedRange>` "defines the range of cited content, often represented by pages or other
  units" (the specific place being pointed at). This is exactly the statute-section /
  marginal-number vs reporter-pagination distinction.
- **`@unit`** — open list; TEI *suggests* `volume, issue, page, line, chapter, part,
  column, entry`. Custom tokens are compliant.
- **`<orgName>`, `<idno>`** — valid in `<bibl>` (`model.nameLike` / `model.biblPart`);
  `@type` open on both.

### 3.3 EpiDoc (real-world TEI community practice)

EpiDoc's bibliography guidance uses **both** elements deliberately: `<biblScope>` in the
master bibliography for the item's extent (`unit="issue"`, `unit="page"`), and
`<citedRange>` in the edition for the pinpoint into the work, with an **extended open
`@unit` list** beyond the TEI suggestions. So the "`biblScope` = extent / `citedRange` =
pinpoint" split, and extending `@unit`, are established TEI practice — not our invention.

### 3.4 CSL 1.0.2 / CSL-M / Zotero (reference-manager vocabulary — the likely crosswalk target)

Legal **item types**: `legal_case`, `legislation`, `bill`, `treaty`, `regulation`,
`hearing`. Legal **variables / Zotero fields**:

| Concept | CSL variable | Zotero field |
| --- | --- | --- |
| court / issuing body | `authority` | `court` |
| docket / file number | `number` | `docketNumber` |
| reporter / code | `container-title` | `reporter` / `code` |
| reporter volume | `volume` | `reporterVolume` |
| first page in reporter | `page` / `first-page` | `firstPage` |
| statute section | `section` | `section` |
| case name / name of act | `title` | `caseName` / `nameOfAct` |
| decision / enactment date | `issued` | `dateDecided` / `dateEnacted` |

Takeaways we can borrow: `legislation` is an exact CSL type name; `section` is an exact CSL
variable name; `caseName` is the exact Zotero field name.

### 3.5 ECLI / CELEX

**ECLI** (European Case Law Identifier, EU Council 2011) is the official identifier for
European court decisions: `ECLI:EU:C:2016:644`. **CELEX** identifies EU legal acts. Both
belong in `<idno type="…">`. There is no equivalent universal ID for German case law; the
*Aktenzeichen* (docket) is the de-facto key.

### 3.6 Akoma Ntoso / LegalDocML (OASIS)

The heavyweight standard for legal documents. It marks up **the norms and judgments
themselves** (FRBR-based URIs, `<ref href="…">`, `<rref>`), not bibliographic citation
strings embedded in scholarly prose. Adopting it for the GROBID tagset would be
over-engineering. Its **Naming Convention URIs** are, however, a good target for an
optional `@ref` on our elements if we ever resolve citations (see Decision H).

---

## 4. Design constraints

1. Every label must survive a round-trip through a GROBID sequence-labeling model.
2. Prefer standard TEI elements; prefer standard attribute *values* (TEI → CSL → ECLI, in
   that order) over invented ones.
3. Keep structural punctuation (`§`, `–`, `Tz.`) inside its semantic element for stable
   tokenisation.
4. The referenceSegmenter must learn each genre's boundary shape — especially that a
   decision legitimately ends with `– Case Name`.

---

## 5. Decisions and options

For each decision: the options, their trade-offs, the standard each aligns with, and a
recommendation. **R** marks the recommended option.

### Decision A — Pinpoint (`§`, `Abs.`, `Rn./Tz.`) vs container pagination

| | Option | Aligns with | Trade-off |
| --- | --- | --- | --- |
| **A1 (R)** | New element `<citedRange unit="…">` for pinpoints; keep `<biblScope>` for the reporter's own volume/issue/page | TEI P5 semantics; EpiDoc practice; CSL keeps `section` separate from `page` | Adds one label to the flavour tagset; needs a post-processing rule |
| A2 | Stay in `<biblScope>`, only add `@unit` values (`section`, `sub-section`, `margin`) | TEI (open `@unit`) | Conflates "extent" and "pinpoint"; the model sees one `biblScope` label doing double duty and can only separate `page` from `margin` by literal text |
| A3 | `<biblScope>` for everything, split `margin`/`page` by regex on `Tz.`/`Rn.` in post-processing only | — | No annotation cost; brittle; loses the distinction in gold data |

**Recommendation: A1.** It is the TEI-sanctioned construct for this exact case and matches
EpiDoc's real-world usage; the extra tagset entry is the price of getting `Tz. 24` out of
the page field for good.

### Decision B — Genre label on `<bibl>`

| | Option | Aligns with | Trade-off |
| --- | --- | --- | --- |
| **B1 (R)** | `<bibl type="legislation">` and `<bibl type="decision">` | `legislation` = exact CSL type; `decision` readable; consistent with existing `type="footnote"` | `decision` is not a standard token (CSL says `legal_case`) |
| B2 | `<bibl type="legislation">` and `<bibl type="legal_case">` | Both exact CSL 1.0.2 type names | `legal_case` reads oddly in XML; underscore style unlike the rest of the schema |
| B3 | No `@type`; identify genre downstream from `<orgName type="court">` etc. | — | Weakest signal for the referenceSegmenter, which is where issue 2b bites |

**Recommendation: B1**, with B2 as a fallback if we decide strict CSL-type parity matters
more than readability. `legislation` is taken from CSL either way.

### Decision C — The court

| | Option | Aligns with | Trade-off |
| --- | --- | --- | --- |
| **C1 (R)** | `<orgName type="court">EuGH</orgName>` | TEI `<orgName>`; CSL `authority` | invented `@type` value `court` (TEI has none) |
| C2 | `<orgName>` with no `@type` | TEI | loses the court/other-institution distinction |

**Recommendation: C1.** Everyone agrees it must not be `<author>`; `type="court"` is a
one-word local token with an obvious meaning.

### Decision D — Docket / case number

| | Option | Aligns with | Trade-off |
| --- | --- | --- | --- |
| **D1 (R)** | `<idno type="docket">` for the *Aktenzeichen*, plus `<idno type="ECLI">` / `<idno type="CELEX">` when present | `docket` = Bluebook/CSL sense of `number`; ECLI/CELEX are official IDs | `docket` invented as a `@type` token |
| D2 | `<idno type="caseNumber">` | self-descriptive | non-standard, longer |
| D3 | keep docket in plain text, only type ECLI/CELEX | ECLI/CELEX | docket (the primary key for German cases) stays unlabeled |

**Recommendation: D1.** Must not be `<title>`. `docket` is short and matches common legal
citation terminology; ECLI/CELEX ride along in their own typed `<idno>`.

### Decision E — Case short-name (`GS Media/Sanoma`)

| | Option | Aligns with | Trade-off |
| --- | --- | --- | --- |
| **E1 (R)** | `<title level="a" type="caseName">` | `caseName` = exact Zotero field; stays in GROBID's `<title>` label | `caseName` invented as a TEI `@type` value |
| E2 | `<title level="m">` (decision as a monograph, its popular name as the title) | TEI title levels | no explicit "this is the party shorthand" marker; competes with reporter `<title level="j">` |
| E3 | `<rs type="caseName">` (referencing string) | TEI-semantically purest (it is a name, not a work title) | `<rs>` is not in GROBID's tagset nor this schema; impractical |

**Recommendation: E1.** Keeps the fragment inside a label GROBID already has, and the value
is lifted straight from Zotero. Combined with Decision B, this is what stops the
referenceSegmenter treating `– GS Media/Sanoma` as a new record (issue 2b).

### Decision F — Statute abbreviation (`UrhG`)

| | Option | Aligns with | Trade-off |
| --- | --- | --- | --- |
| **F1 (R)** | `<title level="m" type="legislation">UrhG</title>`, optional `@key="UrhG"` / `@ref` | CSL puts name-of-act in `title`; GROBID already learns journal abbreviations as `<title>` | `type="legislation"` invented as a `@type` value (mirrors the `<bibl>` type) |
| F2 | `<idno type="legislation">UrhG</idno>` | treats the abbreviation as an identifier | it is a name, not an ID; fights the `<idno>` semantics |

**Recommendation: F1.**

### Decision G — Pinpoint `@unit` vocabulary (values for Decision A's `<citedRange>`)

Recommended controlled list (lowercase, hyphenated, per TEI house style; extends the TEI
suggested list the way EpiDoc does):

| `@unit` | Matches | Source of token |
| --- | --- | --- |
| `section` | `§ 19a`, `Art. 5`, `Sec. 2` | TEI-adjacent; **exact CSL variable** |
| `sub-section` | `Abs. 2` | new |
| `sentence` | `S. 1`, `Satz 1` | new |
| `number` | `Nr. 3` | TEI suggested list / CSL variable |
| `letter` | `lit. b`, `Buchst. b` | new |
| `margin` | `Tz. 24`, `Rn. 20`, `Rdnr. 7`, `mn. 12` | new (marginal number / *Randnummer*) |
| `recital` | `ErwGr. 21` (EU recitals) | new; add when such data appears |
| `page` | explicit "at p. N" pin inside the cited work | TEI suggested list |

Sub-choice for the marginal number token: `margin` (**R**, short) vs `marginal-number`
(explicit) vs `rn` (German-specific, opaque).

### Decision H — Resolution hook (optional, non-blocking)

Whether/how to carry a machine-resolvable identifier on the elements above.

| | Option | Notes |
| --- | --- | --- |
| **H1 (R)** | `@key` for a human-readable short key (`key="UrhG"`), `@ref` for a URI when available (ECLI URI, CELEX URI, `gesetze-im-internet.de`, or an Akoma Ntoso Naming-Convention URI) | `att.canonical` provides `@key`/`@ref` on `<title>`, `<orgName>`, `<idno>`; purely additive, never required for training |
| H2 | no resolution hook for now | simplest; revisit when a resolver exists |

---

## 6. Recommended profile

Adopting **A1, B1, C1, D1, E1, F1, G, H1**.

### 6.1 Element and attribute conventions

| Concept | Markup |
| --- | --- |
| Genre | `<bibl type="legislation">` / `<bibl type="decision">` |
| Statute short-title | `<title level="m" type="legislation" key="UrhG">UrhG</title>` |
| Statute subdivision | `<citedRange>` with `@unit` = `section` / `sub-section` / `sentence` / `number` / `letter` (marker included) |
| Court | `<orgName type="court">` (not `<author>`) |
| Docket / *Aktenzeichen* | `<idno type="docket">` (not `<title>`) |
| ECLI / CELEX | `<idno type="ECLI">` / `<idno type="CELEX">` |
| Case short-name | `<title level="a" type="caseName">` (not `<note>`) |
| Decision / enactment date | `<date type="decision">` / `<date type="enacted">` |
| Reporter / code | `<title level="j">` + `<date>` + `<biblScope unit="page">` (first page) |
| Marginal number | `<citedRange unit="margin">` (not `<biblScope unit="page">`) |

**Boundary rule:** `<biblScope>` carries the container work's own extent (reporter
volume/issue/page, year). `<citedRange>` carries the pinpoint into it. If a decision has no
pagination at all, there is **no** `<biblScope unit="page">` — only `<citedRange
unit="margin">`.

**Separators:** the `–`/`—` before docket and case-name **SHOULD** be left as plain text
inside the `<bibl>`, applied consistently; annotators **MAY** instead use `<label
type="separator">–</label>` but **MUST NOT** mix conventions within a batch.

### 6.2 Examples

`§ 19a Abs. 2 UrhG`

```xml
<bibl type="legislation">
  <citedRange unit="section">§ 19a</citedRange>
  <citedRange unit="sub-section">Abs. 2</citedRange>
  <title level="m" type="legislation" key="UrhG">UrhG</title>
</bibl>
```

`Art. 3 Abs. 1 lit. a DS-GVO`

```xml
<bibl type="legislation">
  <citedRange unit="section">Art. 3</citedRange>
  <citedRange unit="sub-section">Abs. 1</citedRange>
  <citedRange unit="letter">lit. a</citedRange>
  <title level="m" type="legislation" key="DS-GVO">DS-GVO</title>
</bibl>
```

`EuGH, Urt. v. 8.9.2016 – C-160/15, GRUR 2016, 1152 Tz. 24 – GS Media/Sanoma`

```xml
<bibl type="decision">
  <orgName type="court">EuGH</orgName>,
  <date type="decision" when="2016-09-08">Urt. v. 8.9.2016</date> –
  <idno type="docket">C-160/15</idno>,
  <idno type="ECLI">ECLI:EU:C:2016:644</idno>,
  <title level="j">GRUR</title> <date>2016</date>,
  <biblScope unit="page">1152</biblScope>
  <citedRange unit="margin">Tz. 24</citedRange> –
  <title level="a" type="caseName">GS Media/Sanoma</title>
</bibl>
```

`BGH, Urteil v. 20.9.2018 – I ZR 53/17, GRUR 2019, 189 Rn. 20 – Cordoba II`

```xml
<bibl type="decision">
  <orgName type="court">BGH</orgName>,
  <date type="decision" when="2018-09-20">Urteil v. 20.9.2018</date> –
  <idno type="docket">I ZR 53/17</idno>,
  <title level="j">GRUR</title> <date>2019</date>,
  <biblScope unit="page">189</biblScope>
  <citedRange unit="margin">Rn. 20</citedRange> –
  <title level="a" type="caseName">Cordoba II</title>
</bibl>
```

Decision with no pagination — `EuGH, Urt. v. 29.7.2019 – C-476/17, Rn. 65 – Pelham`

```xml
<bibl type="decision">
  <orgName type="court">EuGH</orgName>,
  <date type="decision" when="2019-07-29">Urt. v. 29.7.2019</date> –
  <idno type="docket">C-476/17</idno>,
  <citedRange unit="margin">Rn. 65</citedRange> –
  <title level="a" type="caseName">Pelham</title>
</bibl>
```

### 6.3 Segmentation (`*.referenceSegmenter.tei.xml`)

- Each statutory or court-ruling reference is one `<bibl>`; annotators **SHOULD** set
  `@type="legislation"` / `@type="decision"`.
- The `– Case Name` tail and any trailing `Tz.`/`Rn.` pinpoint **MUST** stay inside the
  preceding `<bibl>`.
- Footnote marker stays `<label>`; multiple references split by `;` stay separate `<bibl>`.

```xml
<listBibl>
  <bibl type="decision"><label>13</label> EuGH, GRUR 2016, 1152 Tz. 24 – GS Media/Sanoma</bibl>
  <bibl type="legislation"> § 19a Abs. 2 UrhG</bibl>
</listBibl>
```

### 6.4 Schema changes (RELAX NG)

Edit the composable sources under `schema/`, then regenerate `docs/schema/` with
`uv run python scripts/build-schema.py` (see `README.md`).

**`schema/grobid.training.references.rng`** — add `@type` to `<bibl>` and a
`references_citedRange` pattern to its child `<choice>`:

```xml
<define name="bibl">
  <element name="bibl">
    <optional>
      <attribute name="type">
        <choice>
          <value>footnote</value>
          <value>legislation</value>
          <value>decision</value>
        </choice>
      </attribute>
    </optional>
    <interleave>
      <text/>
      <zeroOrMore>
        <choice>
          <ref name="label"/>
          <ref name="lb"/>
          <ref name="author"/>
          <ref name="orgName"/>
          <ref name="title"/>
          <ref name="date"/>
          <ref name="biblScope"/>
          <ref name="references_citedRange"/>   <!-- NEW -->
          <ref name="publisher"/>
          <ref name="pubPlace"/>
          <ref name="editor"/>
          <ref name="references_edition"/>
          <ref name="references_ptr"/>
          <ref name="idno"/>
          <ref name="references_note"/>
          <ref name="references_seg"/>
          <ref name="references_ref"/>
        </choice>
      </zeroOrMore>
    </interleave>
  </element>
</define>

<!-- Pinpoint into the cited work: statute section/subsection, or the
     marginal number (Tz./Rn./Rdnr.) of a court decision. Distinct from
     <biblScope>, which carries the container work's own extent. -->
<define name="references_citedRange">
  <element name="citedRange">
    <attribute name="unit">
      <choice>
        <value>section</value>
        <value>sub-section</value>
        <value>sentence</value>
        <value>number</value>
        <value>letter</value>
        <value>margin</value>
        <value>recital</value>
        <value>page</value>
      </choice>
    </attribute>
    <optional><attribute name="from"/></optional>
    <optional><attribute name="to"/></optional>
    <text/>
  </element>
</define>
```

Tighten the locally defined `orgName` pattern:

```xml
<define name="orgName">
  <element name="orgName">
    <optional>
      <attribute name="type">
        <choice>
          <value>court</value>
          <value>jurisdiction</value>
          <value>institution</value>
        </choice>
      </attribute>
    </optional>
    <text/>
  </element>
</define>
```

**`schema/shared/bibl-struct.rng`** — `<title>` already allows an open `@type` plus the
closed `@level` list, and `<idno>` already allows an open `@type`; `type="legislation"`,
`type="caseName"`, `type="docket"`, `type="ECLI"`, `type="CELEX"` validate unchanged.
Enumerate them here only if stricter validation is wanted.

**`schema/grobid.training.references.referenceSegmenter.rng`** — add `@type` to `<bibl>`
(no other structural change):

```xml
<define name="bibl">
  <element name="bibl">
    <optional>
      <attribute name="type">
        <choice>
          <value>footnote</value>
          <value>legislation</value>
          <value>decision</value>
        </choice>
      </attribute>
    </optional>
    <zeroOrMore>
      <choice>
        <ref name="label"/>
        <ref name="lb"/>
        <text/>
      </choice>
    </zeroOrMore>
  </element>
</define>
```

---

## 7. Conformance note

| Name | Status |
| --- | --- |
| `<bibl>`, `<title>`, `<orgName>`, `<idno>`, `<biblScope>`, `<citedRange>`, `<date>`, `<label>` | **Standard TEI P5 elements**, all valid in the positions used here |
| `@type`, `@level`, `@unit`, `@from`, `@to`, `@when`, `@key`, `@ref` | **Standard TEI P5 attributes** (`att.typed`, `att.citing`, `att.canonical`, `att.datable`); `@level` uses the closed TEI list, all others are open datatypes |
| `bibl/@type` = `legislation` | **Borrowed from CSL 1.0.2** item type of the same name |
| `bibl/@type` = `decision`, `footnote` | **Project vocabulary** (`footnote` already in use; CSL's equivalent is `legal_case`) |
| `citedRange/@unit` = `section`, `number`, `page` | **Aligned with CSL variables / the TEI suggested `@unit` list** |
| `citedRange/@unit` = `sub-section`, `sentence`, `letter`, `margin`, `recital` | **Project vocabulary** (open datatype; EpiDoc sets the precedent for extending `@unit`) |
| `orgName/@type` = `court` | **Project vocabulary**; concept = CSL `authority` |
| `idno/@type` = `docket` | **Project vocabulary**; concept = CSL `number` (docket sense) |
| `idno/@type` = `ECLI`, `CELEX` | **Official external identifier schemes** (EU) |
| `title/@type` = `legislation` | **Project vocabulary**, mirrors `bibl/@type` |
| `title/@type` = `caseName` | **Borrowed from the Zotero field name** |

No TEI-published taxonomy exists for `bibl/@type`, `orgName/@type`, `idno/@type`, or an
exhaustive `@unit` list, so project-defined values there are expected by the standard, not a
deviation from it.

## 8. Rollout plan

1. Resolve the open sub-choices in §5 (esp. B1 vs B2, `margin` token).
2. Land the §6.4 schema changes and regenerate `docs/schema/`.
3. Add a "Legal references" section to `docs/guidelines.md` linking here, with the §6.2
   examples.
4. Re-annotate the Duranteye (2020) batch for both the references and referenceSegmenter
   models.
5. Retrain; evaluate on held-out legal footnotes, tracking marginal-number-vs-page
   confusion and case-name segmentation splits specifically.
6. Implement the downstream mapping (`<citedRange>` → output profile;
   `<orgName type="court">` / typed `<idno>` / typed `<title>` pass through; optionally a
   CSL `legal_case` / `legislation` crosswalk).

## 9. Open questions

1. `<bibl type="decision">` vs `<bibl type="legal_case">` (Decision B).
2. `<citedRange>` in the *final* output — keep it, or fold into `<biblScope>` with the
   extended `@unit`?
3. Parallel reporter citations (`GRUR 2016, 1152 = NJW 2016, 3441`) — one `<bibl>` with
   repeated `<title level="j">…<biblScope>` blocks (current assumption) or split?
4. Docket `@type` token: `docket` vs `caseNumber` vs CSL-plain `number`.
5. Do we need `unit="recital"` now, or add it only when EU-regulation recitals appear?

## 10. References

- Issue #41 — <https://github.com/mpilhlt/grobid-footnote-flavour/issues/41>
- TEI P5 Guidelines — `att.citing` (`<biblScope>`, `<citedRange>`), `att.typed`,
  `att.canonical`, `<orgName>`, `<idno>`, `<title>`, `<bibl>` content model.
- EpiDoc Guidelines — "Encoding the Bibliography" (`<biblScope>` vs `<citedRange>`,
  extended `@unit`). <https://epidoc.stoa.org/gl/latest/supp-bibliography.html>
- Citation Style Language 1.0.2 specification — legal item types and variables.
  <https://docs.citationstyles.org/en/stable/specification.html> ;
  CSL-M extensions <https://citeproc-js.readthedocs.io/en/latest/csl-m/>
- European Case Law Identifier (ECLI) — EU Council conclusions 2011;
  <https://e-justice.europa.eu/topics/legislation-and-case-law/european-case-law-identifier-ecli-search-engine_en>
- Akoma Ntoso / OASIS LegalDocML — XML vocabulary and Naming Convention.
  <https://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0-part1-vocabulary.html>
- Foppiano & Boulanger, "Digging Up Citations: FOSSIL …" — <https://arxiv.org/abs/2606.01109>
  (context for this work; contains no legal-citation tagset — this spec proposes one for it)
- Duranteye (2020), `10.5771/2699-1284-2020-1-16`.
