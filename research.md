# tf-build research

## Question

Which concerns repeated across the current Text-Fabric conversion projects are genuinely corpus-independent enough to extract into a shared package?

## Evidence inspected

This bootstrap research compared current code and documentation in:

- `alexsosn/ORAEC-TF`
  - `src/oraec_tf/source.py`: immutable full-SHA validation, clean checkout verification, staged Git acquisition, atomic installation.
  - `src/oraec_tf/cli.py`: source-info/fetch/verify command surface.
- `alexsosn/CopticScriptorium-TF`
  - `copticscriptorium_tf/converter.py`: immutable provenance validation, fresh destination contract, parse/build/write orchestration, timings, peak RSS, output file/byte counts, structured conversion result.
  - `copticscriptorium_tf/agora.py`: network-free materializer adapter over an Agora-owned empty staging root.
  - `copticscriptorium_tf/writer.py`: isolated TF writing, metadata projection, valued/unvalued edge serialization, output safety.
- `alexsosn/TLHdig-TF`
  - current build/research documents: clean replacement builds, stale `.tf` feature hazards, clean reload validation, release predecessor/reproducibility gates, generated feature documentation.
- `annotation/text-fabric`
  - `tf/convert/walker.py`: `CV.walk` already owns generic slot/node/edge emission plus metadata, graph and feature validation.
- `annotation/text-fabric-factory`
  - `tff/docs/main/top.md`, `tff/convert/tei.py`, `tff/convert/xml.py`: upstream package already covers generic XML, TEI and PageXML conversion and XML schema tooling.

The compared projects use different source models and scholarly graph semantics. Their duplicated infrastructure is concentrated around source identity, filesystem safety, build orchestration, validation, provenance and materializer hosting.

## Findings

### Extract now

1. **Source identity and acquisition**
   - immutable Git commit validation;
   - clean checkout verification;
   - source snapshot records;
   - deterministic/staged acquisition;
   - archive/download verification later where an actual second consumer exists.

2. **Safe build workspace**
   - reject unsafe or pre-existing destinations by explicit policy;
   - reject symlink surprises;
   - isolate temporary/staging output;
   - publish only after validation.

3. **Build orchestration and reports**
   - phase timings;
   - output counts/bytes;
   - optional peak-memory measurement;
   - stable machine-readable build result/provenance.

4. **TF artifact validation**
   - generated artifact exists and contains expected TF files;
   - clean reload with supported Text-Fabric;
   - required feature/value-type/metadata checks;
   - stale-file detection when replacement semantics are promised.

5. **Reproducibility/provenance**
   - source repository/revision;
   - source/archive hashes where applicable;
   - converter/package version;
   - deterministic artifact manifest/fingerprint.

6. **Feature documentation helpers**
   - derive reference pages/inventories from emitted TF headers/schema rather than maintain a second manual feature list.

7. **Agora adapter helpers**
   - validate host-owned empty output workspace;
   - keep conversion network-free;
   - write stable relative artifact paths and build reports.

### Extract only after more evidence

A generic writer-independent `TFGraph` representation may be useful, but CopticScriptorium-TF currently provides only one strong implementation precedent. Do not freeze a shared graph API until at least two materially different converters can use it without leaking corpus semantics.

### Keep project-local

- source parsers;
- canonical corpus IRs;
- scholarly normalization;
- slot type and node/edge ontology;
- source-specific identifiers and relations;
- EpiDoc, ORACC, TT, ORAEC, AOxml semantics;
- corpus-specific `otext` choices and rendering policy.

### Explicit non-goal: universal XML/TEI converter

Text-Fabric-Factory already provides generic XML/TEI/PageXML conversion machinery. tf-build should provide interoperable build/materialization primitives that such converters can use, not duplicate their parsing stack.

## Architectural consequence

tf-build should be a small composable library, not a `BaseCorpusConverter` inheritance framework. Prefer immutable dataclasses, small functions and narrow protocols. Corpus projects should remain able to use Text-Fabric `CV.walk` or direct `Fabric.save` according to measured needs.

## First extraction candidate

The ORAEC-TF source identity/acquisition implementation is the best initial behavior to extract because it is small, already tested conceptually by a real consumer, and overlaps with provenance constraints in CopticScriptorium-TF. The first implementation ticket after bootstrap should specify that API from real consumer requirements rather than copying ORAEC names verbatim.
