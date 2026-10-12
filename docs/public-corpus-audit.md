# Public Text-Fabric corpus-builder coverage

This is a maintainer-level portfolio check for public, non-fork repositories
owned by `alexsosn` that generate native Text-Fabric corpora or feature modules.
It is independent of, and does not replace, converter integration tests.

The repository inventory is obtained live from GitHub. A public non-fork repository
whose name ends in `-TF` (case-insensitive), or is named
`BHSA-cantillation-trees`, is in scope. Private repositories, forks, generic
TF tooling (`tf-build`, `tf-jev`, and similar tools), notebooks, and
analytical projects that do not generate TF outputs are excluded. Update the
detector when a new corpus builder uses a different naming convention.

| Classification | Repositories |
| --- | --- |
| Implemented native TF corpus or feature module | BHSA-cantillation-trees, CATSS-TF, CTC-TF, CopticScriptorium-TF, IIP-TF, ORACC-TF, ORAEC-TF, Pseudepigrapha-TF, TLHdig-TF |
| Pending, tracked by an open implementation issue | [PG-TF #3](https://github.com/alexsosn/PG-TF/issues/3), [OpenGreek-TF #6](https://github.com/alexsosn/OpenGreek-TF/issues/6) |

An implemented project need not distribute upstream data or have a published
release. Actual native TF generation (standalone corpus or module) is the
criterion. A README, app configuration, wrapper, or dependency on Text-Fabric
by itself is insufficient evidence of implementation.

## CI gate

The workflow `.github/workflows/public-tf-coverage.yml` runs on every push
and PR in this repository, weekly on Monday, and through manual dispatch.
It executes offline policy unit tests, then uses the GitHub public API to:

1. discover public, non-fork TF corpus builders and fail on any missing from the
   classification;
2. verify that each implemented builder has at least one GitHub Actions
   workflow (the individual repository must validate its converter);
3. verify that implementation tickets for pending projects remain **open**;
4. fail closed if the API cannot verify a required item.

When a tracked issue is completed, first add native TF build-and-reload tests
to that repository's CI, then move its name from `TRACKED` to `IMPLEMENTED`.
Do not close a ticket and leave the project classified as pending.

**Evidence boundary:** this portfolio gate proves inventory coverage, issue
state, and workflow presence, not the correctness of a remote converter or the
contents of every remote CI job. Individual corpus CI must exercise generation,
`tf.fabric.Fabric.load` or `loadAll`, source conservation invariants, and at
least one representative feature/query on fixtures or pinned real source data.
Failing user-facing end-to-end acceptance should block a release of that corpus.

To run policy tests offline:

```sh
python -m unittest discover -s tests -p test_public_tf_corpora.py -v
```

The GitHub live audit is:

```sh
python scripts/audit_public_tf_corpora.py
```
