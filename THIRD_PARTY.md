# Third-party attribution and licenses

[简体中文](THIRD_PARTY.zh-CN.md) · [Documentation](docs/README.md)

## Amelia

The statistical method and reference implementation are by **James Honaker, Gary King and Matthew Blackwell**. Bootstrap–EM is not an original method introduced by this project.

- Reference: Amelia **1.8.3**, distributed upstream under GPL (>= 2).
- [Official source archive](https://cran.r-project.org/src/contrib/Amelia_1.8.3.tar.gz).
- Archive SHA-256: `7699455ca3e9dabd60ad0ec69185ece3f24a597ef8da18033ea0b7a32356967f`.
- Audited files include `R/emb.r`, `R/prep.r`, `R/amcheck.r` and `src/em.cpp`. Observed semantics and exceptions are documented in the [algorithm contract](docs/algorithm-contract.md).
- Reference fixtures use synthetic project data processed by unmodified Amelia. See [fixture provenance](tests/fixtures/reference_amelia/README.md) and `scripts/export_reference_fixtures.R`. Upstream archives remain in the ignored cache.

The port is distributed under **GPL-3.0-only**, with the full text in [LICENSE](LICENSE). Original authorship and source attribution remain applicable.

## Data

The UCI pages for Covertype, Individual Household Electric Power Consumption and Year Prediction MSD identify **CC BY 4.0**. Authors, DOIs, downloads, hashes and transformations are recorded in [the manifest](data/manifest.json), [sample notes](data/samples/README.md) and [data guide](docs/datasets.md). Data and software licenses apply separately; attribution must accompany redistribution.

## Dependencies

PyTorch, NumPy, SciPy, reticulate and other dependencies retain their own licenses. Virtual environments, R libraries and download caches are not bundled in the repository.
