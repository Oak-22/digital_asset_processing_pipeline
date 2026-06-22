# Production Workflow System Design & Implementation: Metadata Application, Enrichment, and Query Pipeline

Part of the **Creative Workflow Batch Transformation Pipeline** umbrella project.

<br>

## Executive Summary

This stage establishes a safe metadata foundation for downstream image
workflow operations. Because ingest supports only a single metadata
preset, the workflow establishes a stable identity baseline first, then
applies semantic enrichment post-import with tightly controlled overlap.
The result is a metadata model that is auditable, scalable
across multiple classification domains, and useful for downstream
retrieval through ad-hoc filtering and Smart Collections. Operationally,
this improves internal organization and retrieval while producing structured
semantic metadata that could later support analytics, search, or machine-learning workflows.

Within the larger pipeline, Stage 1 is the deterministic state layer:
it makes image records identifiable, queryable, and safe to enrich
before later culling, visual conditioning, or AI-assisted operations
introduce more subjective and probabilistic decision points.

<br>

---

<br>

## Problem

Metadata application during ingest is constrained by Lightroom's
single-preset import model. That makes it easy to initialize ownership
metadata consistently, but risky to mix protected identity fields with
later semantic enrichment fields in the same write path.

The core challenge is to maintain a stable, authoritative identity
state while enabling iterative, revisable semantic enrichment. Poorly
structured metadata increases rework, weakens retrieval, and reduces
the downstream usefulness of image records for curation, publishing,
internal discoverability, and later pipeline stages.

This stage intentionally resolves the most deterministic part of the
system first. Later stages operate on visually variable images and
AI-derived semantic outputs; Stage 1 ensures those later transformations
remain anchored to stable source records and retrievable metadata.

<br>

---

<br>

## Solution Overview

The workflow separates metadata into a protected identity layer and a
revisable semantic layer. A single import preset establishes the
ownership baseline at ingest, while domain-specific semantic presets are
applied only after import with mostly non-overlapping field writes.
Keywords are also managed post-ingest so classification remains
deliberate and incremental. In this implementation, the main documented
exception is `Contact > Job Title`, where the domain preset can refine a
generic ingest value such as `Photographer` into a domain-specific value
such as `Wedding Photographer`. Once enriched, the metadata supports
query-driven retrieval, including Smart Collections treated as
declarative views over image records.

> [!IMPORTANT]
> **Governing Principle:** Establish protected metadata state first, then
> layer revisable semantic enrichment and query logic on top of it.
>
> **Governing Principle:** Each metadata field should have one default
> write owner. Overlap is allowed only as an explicit refinement
> exception.

<br>

---

<br>

## Key Constraints

- ingest supports only one metadata preset; there is no native preset stacking
- Lightroom provides no field-level locking for protected metadata fields
- post-import presets remain safe only when checked-field writes do not overlap
- metadata presets can overwrite existing values when the same checked fields are reused
- export controls are reductive (include/exclude), not additive

Because the tool does not provide native field isolation, the workflow
enforces write isolation through schema design: the ingest preset owns
the stable identity baseline, while later semantic presets write
primarily to non-overlapping semantic fields. Where a later preset
intentionally refines an existing value, that overlap must be explicit,
documented, and reviewable.

<br>

---

<br>

## Technical Design & Implementation

<br>

### Separation of Concerns

- **Identity Layer**: protected, authoritative ownership/authorship state initialized at ingest.
- **Semantic Layer**: mutable, revisable classification/context state enriched post-ingest.
- **Refinement Exception Layer**: narrowly scoped, intentional post-ingest updates to baseline metadata where domain context adds specificity.
- **Query Layer**: declarative logical views derived from metadata predicates (Smart Collections).

```text
RAW Image
   ↓
[Copyright & Creator Import Preset] -> Identity Layer (Protected)
   
   ↓ (post-import)
[Domain Presets] -> Semantic Layer (Mutable)

   ↓
[Smart Collections]
   ↓
Derived Logical Views
```

<br>

### Implementation Details

<br>

### 1) Single Global Import Preset (Authoritative)

**Metadata Preset name:** `[IMPORT] Global Copyright & Creator`

Included identity fields:
- IPTC Copyright
- Copyright Status
- Rights Usage Terms
- Creator Name
- Creator Email
- Creator Website
- Creator Job Title
- Credit Line

Excluded fields:
- Caption
- Headline
- IPTC Category
- Keywords
- Accessibility Alt Text
- Domain-specific descriptions

<br>

**Preset Panel**

The preset panel itself is part of the evidence here because it shows
the write scope before import. In this stage, the import preset is
configured to initialize only the authority-bound identity fields listed
above.

<br>

![Import preset panel before write](assets/images/001_stage1-import-preset-panel-before-write.png)

*Figure: Import preset configuration before write. The checked fields define the ingest-time identity baseline that will be applied uniformly to the entire batch of images at import.*

<br>
<br>

![Import metadata full view after write](assets/images/002_stage1-import-metadata-full-view-after-write.png)

*Figure: Full Lightroom view after the import preset has been applied. The image provides workflow context while showing the authoritative metadata baseline now present on the asset.*

<br>
<br>

![Import metadata detail view after write](assets/images/003_stage1-import-metadata-detail-view-after-write.png)

*Figure: Metadata panel detail after import. This closer view is more legible.*

<br>
<br>

### 2) Domain-Specific Presets (Post-Import Only)

**Metadata Preset name(s):**

`Graduation — CSU Sacramento` | `Wedding` | `Marketing`

Domain presets are semantic enrichment presets applied after ingestion.

- Identity/authorship/copyright fields remain unchecked except for explicitly documented refinement cases.
- Most checked fields are semantic fields.
- In this workflow, `Contact > Job Title` is the main intentional overlap: a general ingest value such as `Photographer` may be refined to a domain-specific value such as `Wedding Photographer`, or any other domain-specific variant (`[INSERT DOMAIN] Photographer`). These selective metadata overwrites are intended primarily to increase external discoverability by adding domain-specific professional context, while also marginally improving downstream retrieval and internal discoverability.
- Example semantic fields: Caption, Headline, IPTC Category, Accessibility Alt Text, contextual descriptions.
- In this workflow, `Content > Description` is the clearest domain-specific metadata consequence of the post-import preset. A field such as `Wedding Photography by Julian Buccat – professional wedding photographer based in California, specializing in timeless, candid, and editorial-style wedding photos.` is intended primarily for external discoverability, while still supplying richer contextual metadata for downstream retrieval and catalog interpretation.

Location metadata is a separate classification dimension from domain.
Because a domain such as `Wedding` or `Marketing` can occur across many
regions, IPTC Image location fields in the metadata presets are too context-sensitive to be
safely embedded in a broad domain preset by default. In practice,
selective keyword-based location tagging is often the safer batch
mechanism, post-presets.

<br>

**Preset Panel**

The domain preset panel shows the second write path before application.
This is where the workflow deliberately constrains semantic enrichment to
its intended fields and, where needed, documents any narrow refinement
overlap with the ingest baseline.

<br>

![Domain preset panel before write](assets/images/004_stage1-domain-preset-panel-before-write.png)

*Figure: Domain preset configuration before write. The checked fields define the semantic enrichment scope that will be layered onto the ingest-established metadata baseline.*

<br>
<br>

![Layered metadata full view after write](assets/images/005_stage1-layered-metadata-full-view-after-write.png)

*Figure: Full Lightroom view after the domain preset has been applied on top of the import baseline. The combined state now includes both preserved identity metadata and domain-specific enrichment.*

<br>
<br>

![Layered metadata detail view after write](assets/images/006_stage1-domain-layered-metadata-detail-view-after-write.png)

*Figure: Combined identity and domain metadata view*

<br>
<br>

### 3) Keywords Managed Separately

Keywords are intentionally excluded from the global ingest preset.
- Taxonomy evolves incrementally as the culled image set is reviewed and
  the keyword hierarchy is refined over time.
- Keyword assignment is explicit and post-ingest (Keyword List/Keyword Sets or semantic presets).
- This preserves deliberate classification rather than implicit ingest-time tagging.

<br>

**Keyword Lists**

Keyword Lists function as hierarchical taxonomies for scalable
semantic metadata management.

This is more useful than a flat keyword set alone when the hierarchy
captures real semantic dependency rather than convenience. Flat
keywords can label isolated concepts, but a keyword taxonomy can also
preserve parent-child structure where that structure is meaningful,
making classification easier to extend, browse, audit, and reuse across
adjacent domains. That added structure improves retrieval ergonomics
and internal discoverability today, and creates cleaner semantic inputs
for later analytics, potential machine-learning workflows, and any
downstream systems that index exported metadata for external
discoverability.

The important boundary condition is that not every concept benefits from
being nested. Once a hierarchy starts binding together independent
dimensions that should remain composable at query time, the better
design moves back toward a flatter taxonomy in those areas.

<br>

![Keyword list full view](assets/images/007_stage1-keyword-list-full-view.png)

*Figure: Full Lightroom view of the Keyword List workspace. This shows where keyword taxonomy is managed as a separate post-ingest classification surface rather than being collapsed into the import preset.*

<br>
<br>

**Keyword Taxonomy Design: When Hierarchy Helps vs Hurts**

Hierarchy is only useful when the child term truly depends on the
parent term for meaning. The diagram below makes the threshold explicit:
once independent dimensions are overnested under a parent such as
`Wedding`, the taxonomy becomes less reusable and harder to query
cleanly across adjacent domains, so the design should be normalized back
toward a flatter, more composable structure in those areas. The
taxonomy evolution is easier to understand when viewed side by side
before the individual intermediate states are examined in detail.

![Keyword taxonomy semantic normalization overview](assets/diagrams/stage1-keyword-taxonomy-semantic-normalization.jpg)

*Figure: Side-by-side taxonomy evolution from overnested event-centric hierarchy to a more composable semantic classification structure. The sequence shows where hierarchy adds value, where it crosses the threshold into semantic coupling, and why parts of the taxonomy are intentionally flattened back out while true specialization boundaries are retained.*

<br>
<br>

This evolution also mirrors classical schema normalization in database
design. Early keyword hierarchies often behave like denormalized
structures where multiple independent semantic dimensions are tightly
coupled beneath a single parent category. As the taxonomy matures,
reusable concepts are decomposed into more independent classification
dimensions, reducing semantic coupling and improving query
composability, reuse, and extensibility across domains. In this sense,
the workflow performs a form of semantic schema normalization over the
catalog metadata layer.

<br>
<br>

The following detailed figures show the intermediate states that led to
that final structure.

<br>

![Overnested keyword taxonomy example](assets/images/009_stage1-keyword-taxonomy-overnested.png)

*Figure: Overnested taxonomy design. Here, several independent dimensions are incorrectly bound under `Wedding`, even though they also apply to engagement sessions, branding work, graduation sessions, corporate events, or venue classification more broadly.*

<br>
<br>

In the first version above, terms such as `First Look`, `Outdoor`, `Church`,
and even `Cocktail Hour` are too tightly coupled to `Wedding`.
Operationally, that hurts reuse because those concepts can also describe
other session types, locations, or event structures. If a reader or
operator needs `Cocktail Hour` and `Wedding`, those dimensions should be
combined at query time rather than fused permanently into one subtree.

![Improved keyword taxonomy example](assets/images/010_stage1-keyword-taxonomy-improved.png)

*Figure: Improved taxonomy design. The hierarchy is reduced so only clearly dependent structures remain nested, while reusable concepts are promoted to their own top-level classification dimensions.*

The improved version separates event identity from other dimensions.
`Location (Type)` becomes its own classification surface rather than a
subtree of `Wedding`, and general moments remain distinct from
wedding-specific moments. This is the point where hierarchy starts to
help rather than hurt: the structure becomes easier to extend without
forcing cross-domain reuse through one event-specific parent.

![Further rationalized keyword taxonomy example](assets/images/011_stage1-keyword-taxonomy-superior.png)

*Figure: Final taxonomy structure. Additional review revealed that some seemingly wedding-exclusive moments were still cross-event concepts, so they were promoted out of the wedding-only subtree while finer-grained nested structure was retained only where it represented true specialization. As a result, `Wedding` now functions as a single top-level event identity rather than as a parent container for unrelated dimensions.*

This final revision sharpens the design rule: nesting is still useful,
but only when it expresses genuine specialization rather than
convenience. `Celebration` can retain nested subterms because those
children are finer-grained variants of the same parent concept. By
contrast, terms such as `father daughter dance` or `first dance` become
less useful when treated as inherently wedding-exclusive if they can
also function as cross-event moments in the broader taxonomy.

<br>

**Exported Keyword Evidence**

The keyword taxonomy improvement was validated by comparing the archived
pre-tightening snapshot against the tightened Stage 1 keyword snapshot:

```bash
diff -u \
  outputs/stage1/snapshots/04_post_keywords_before_keyword_tightening.json \
  outputs/stage1/snapshots/04_post_keywords.json
```

That comparison showed that keyword tightening reduced avoidable
metadata noise in the Stage 1 output. The tightened snapshot narrows the
evidence surface to the keyworded college-graduation assets and removes
unrelated descriptive fields from the keyword-focused output.

The remaining repetition between `subject` and `hierarchical_subject`
reflects Lightroom's native keyword export behavior rather than a
taxonomy design failure. Lightroom serializes both flat keyword terms
and hierarchical keyword paths, so parent categories and terminal
keywords can appear redundantly across records even when the intended
keyword tree is well-structured. For example, a hierarchical path such
as `Location|Geography|USA|California|Sacramento` can also appear as
individual flat `subject` terms: `Location`, `Geography`, `USA`,
`California`, and `Sacramento`.

<br>

---

<br>

## Verification (Critical)

<br>

### During Import

1. Apply only `[IMPORT] Global Copyright & Creator` during ingest.

<br>

### After Import

1. Review 1-2 sample images from the ingested batch in the Library
   module.
2. Switch the metadata panel to **IPTC**.
3. Validate identity fields are populated (copyright + creator fields).
4. Validate semantic/classification fields are still empty.

<br>

### After Applying One Domain-Specific Semantic Preset

1. Re-check the metadata panel in **IPTC**.
2. Validate semantic fields are now populated.
3. Validate identity fields remain unchanged from ingest baseline except for any explicitly intended refinement fields such as `Contact > Job Title`.
4. Confirm resulting state is additive and non-destructive.

<br>

> [!IMPORTANT]
> **Governing Principle:** Authorship metadata should be automatic and irreversible.
> Semantic metadata should be deliberate and revisable.

<br>

---

<br>

## Downstream Querying — Exploratory Queries (Library Filtering) and Declarative Views (Smart Collections)

<br>

### Two Query Modes

After establishing a repeatable metadata schema strategy, the catalog
supports two distinct query modes:

- **Library Filtering** = exploratory, one-off queries over catalog metadata
- **Smart Collections** = saved declarative views over the same metadata store

Both depend on the same enriched metadata foundation. The difference is
whether the query is transient or saved for repeated reuse.

<br>

### Systems Framing

Smart Collections can be understood as a query and indexing layer over
stable metadata-backed source records, not just as an organizational UI
feature. This makes their behavior more legible in systems terms.

<br>

### Conceptual Model

- Photos = source records
- Metadata-backed attributes (ratings, flags, keywords, dates, capture attributes) = structured columns
- Library filtering = exploratory one-off queries
- Smart Collections = saved predicates / declarative views

Stage 1 does not create every queryable field in the catalog; it
standardizes and enriches the subset of metadata this workflow
explicitly controls, increasing overall metadata diversity. Other queryable attributes may be camera-generated or added later in the workflow. For example, ratings and flags may be
assigned during culling after Stage 1 and before Stage 2.

Collections store selection logic, not copies of records. Membership is continuously recomputed as metadata changes, making them functionally similar to views in an RDBMS.

<br>

---

<br>

## Ad‑hoc Library Filtering

The Library Filter bar performs temporary, exploratory metadata queries
against the catalog. Users can filter images based on fields such as:

- Rating
- Flags
- Capture date
- Camera model
- Lens metadata

This mode is useful for one-off investigation and operational review
when the goal is to inspect the catalog from a temporary analytical
angle rather than save a reusable retrieval rule.

<br>

### Example: Exploratory Gear Review

Conceptual SQL equivalent:

```sql
SELECT camera_model, lens_model, COUNT(*) AS strong_images
FROM images
WHERE rating >= 4
GROUP BY camera_model, lens_model;
```

This kind of temporary filtering is useful for exploratory review, such as evaluating which camera body and lens combinations are producing the strongest images.

![Ad-hoc library filter example](assets/images/012_stage1-ad-hoc-library-filter-example.png)

*Figure: Temporary Library Filter query over catalog metadata for exploratory retrieval. This mode supports quick operational inspection without creating a saved declarative view.*

<br>

---

<br>

## Smart Collections

Smart Collections store reusable selection logic over the enriched
metadata layer. Unlike temporary library filters, they preserve the
query definition itself so the same retrieval rule can be revisited,
reused, and refined over time.

<br>

### Example: Best of Graduation 2025 as Derived Dataset

A “Best of Graduation 2025” view can be defined as:
- Capture Date is in the range `2025-01-01` to `2025-12-31`
- Rating = 5
- Keywords contains all `graduation`

This produces a highly contextualized derived dataset for downstream review, curation, and portfolio selection.

Conceptual SQL equivalent:

```sql
SELECT *
FROM photo_catalog
WHERE capture_date BETWEEN '2025-01-01' AND '2025-12-31'
  AND rating = 5
  AND keyword_terms LIKE '%graduation%';
```

The SQL examples in this section are conceptual analogues, not claims
about Lightroom’s literal internal query representation. The catalog may
store rule definitions in SQLite-backed tables, but the system’s
internal execution model is not directly exposed through the GUI.

The point is that Smart Collections behave like saved declarative views
over enriched metadata.

---
![Smart Collection Example] (assets/images/013_stage1-smart-collection-example.png)
---

<br>

### Smart Collection Value

- Makes curation logic explicit, inspectable, and reusable.
- Reduces repeated manual filtering during review and selection.
- Turns Smart Collections into a more reliable retrieval layer for ongoing workflow decisions by supplying better structured metadata.

<br>

### Smart Collection Limitations

- No joins across entities
- Limited computed-field expressiveness
- No built-in versioning of query definitions
- No exportable formal schema for rules

<br>

---

<br>

## Resulting Benefits of Stage 1

- protected identity metadata established at ingest
- revisable semantic enrichment layered without destructive field overlap
- clearer separation between authority-bound metadata and descriptive metadata
- more reusable classification through post-ingest keyword taxonomy management
- faster and more reliable retrieval through ad-hoc filtering and Smart Collections
- stable metadata state before subjective culling and downstream image transformation

<br>

---

<br>

## Engineering Concepts Demonstrated

- Deterministic metadata initialization under a single-preset ingest
  constraint
- Identity vs semantic metadata partitioning
- Controlled metadata refinement through primarily non-overlapping field assignments with explicit exceptions
- Keyword taxonomy management as a separate semantic classification
  layer
- IPTC-panel verification as an operator-visible metadata validation
  checkpoint
- Smart Collections as saved declarative views 
- Ad-hoc library filtering as exploratory one-off querying

<br>

---

<br>

## Takeaway

Stage 1 turns metadata application from an ad hoc cataloging habit into
a deterministic state-initialization and retrieval system. By
separating protected identity metadata from later semantic enrichment
and query logic, it creates the stable, searchable foundation that the
later visual-conditioning and AI-assisted stages depend on.
