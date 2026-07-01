# Mapping methodology

## Direction

Every mapping reads **subject (source) `predicate` object (ECCDM hub)**.
The subject is always a source-dataset element; the object is always an ECCDM
hub element (`eccdm:` prefix). This is why the predicate semantics matter: they
describe the *source relative to the hub*.

## Predicates (SKOS)

| predicate | meaning (subject vs object) | use when |
|---|---|---|
| `skos:exactMatch` | semantically equivalent | same concept, same granularity |
| `skos:closeMatch` | nearly equivalent, minor semantic drift | e.g. administrative sex vs sex-at-birth |
| `skos:broadMatch` | **subject is broader** than the hub element | one source field maps to several hub fields |
| `skos:narrowMatch` | **subject is narrower** than the hub element | source splits one hub concept into many |
| `skos:relatedMatch` | associated but not subsumption | weak/contextual relation |

> Mnemonic: `broadMatch` means *the source field is broader*. The oBDS single
> `Diagnosedatum` is **broader** than ECCDM `visitDate` (which is one of four
> separate diagnosis-date fields), so it's `broadMatch` to each.

For "this source element has **no** equivalent in the hub", do **not** invent a
row — its absence from the mapping set *is* the finding. Use the hub-side gap
report (`coverage.py`) for the inverse (hub elements no source covers).

To assert an explicit *negative* ("source X deliberately has nothing for hub
element Y"), use `predicate_modifier = Not` with the relevant predicate rather
than omitting the row, so the decision is recorded.

## Justification (`semapv`)

- `semapv:ManualMappingCuration` — curated by hand (default here)
- `semapv:LexicalMatching` — matched by label similarity
- `semapv:CompositeMatching` — derived from other mappings

## Confidence

Float `0.0–1.0`. Convention used in the seed set:

- `0.9–1.0` — unambiguous, same terminology recommended on both sides
- `0.6–0.8` — equivalent concept but granularity/value-set differences
- `< 0.6` — known semantic drift; read the `comment`

## Two layers

This crosswalk currently maps at the **element / structural** layer (which field
corresponds to which field). A second **value / terminology** layer (mapping the
*codes* inside an element — e.g. oBDS laterality vs ECCDM laterality value set)
can be added as separate SSSOM sets, e.g.
`mappings/value/<source>-laterality__to__eccdm.sssom.tsv`. Keep them separate so
element coverage and code coverage are reported independently.

## Non-standard extension columns

SSSOM allows extra columns beyond its core slots (documented in the `#` header).
This crosswalk uses:

| column | meaning | values |
|---|---|---|
| `subject_terminology` | code system the source element binds | free text / `—` (deferred) |
| `mapping_cardinality` | element multiplicity source↔hub | `1:1`, `n:1`, `1:n`, `n:n` |
| `element_kind` | SDTM/ADaM class of the source element | `collected`, `calculated` |
| `source_context` | the capture-context axis the source indexes the concept by | see below |
| `review_status` | curation state | `proposed`, `reviewed` |

### `source_context` — the collision resolver

Some sources record the **same clinical concept multiple times**, indexed by a
cross-cutting dimension. `source_context` names that dimension so an n:1 fan-in
to one hub element is explicit rather than arbitrary. The values are
**source-specific**:

| source | dimension | values |
|---|---|---|
| NABON | MDO (tumour-board) phase | `preoperatief`, `postoperatief`, `neoadjuvant`, `metastase`, `recidief` |
| oBDS | Meldeanlass / time reference | `Diagnose`, `Verlauf`, `Pathologie`, `Tod` |
| ECCDM (hub) | — (the hub is the context-free reference) | *(blank)* |

**Rule:** two rows with the *same* `object_id` **must** differ in
`source_context` — otherwise it is a genuine duplicate conflict, not a context
split. It is orthogonal to `predicate_id` (context = *which*; predicate = *how
equivalent*). Keeping e.g. NABON `postoperatief` rows alongside `preoperatief`
ones surfaces hub limitations (ECCDM collapses the pre/post-op distinction into
a single field → information loss made visible).

## CURIEs

Source models do not publish per-element IRIs, so prefixes in `prefixes.yaml`
are **minted for this crosswalk**. Element ids follow `<prefix>:<group>.<field>`
(e.g. `obds:diagnose.icdo3_histologie`, `eccdm:CancerStage.stage`). The hub ids
come straight from `extract_eccdm_hub.py` as `eccdm:<Model>.<path>`.
