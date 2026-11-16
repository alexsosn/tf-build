# #115: Classify `manuscript_reviewer` based on its actual outputs

## Evidence / research

The fail-closed [public TF producer inventory run 43963206118](https://github.com/alexsosn/tf-build/actions/runs/43963206118) on tf-build docs PR #114 rejected one new unclassified public non-fork owner repository, `manuscript_reviewer`. The audit itself is operating as designed; do not modify its detection or remove this failure class.

Inspected [current public source README](https://github.com/alexsosn/manuscript_reviewer/blob/main/README.md). The repository explicitly presents itself as `Manuscript reviewer — Syriac validator`, a local Electron editor for BL Add MS 14,470 images, PAGE XML line/region geometry and Syriac transcriptions. It aligns reference fragments, edits the PAGE XML and supports explicit Transkribus upload. Its original manuscript PAGE files are stored in a *different* repository. The README does **not** describe output of a native Text-Fabric corpus or any `*.tf` features. There is no evidence to add it as a TF corpus producer.

## Plan / acceptance

Add this repository to the existing alphabetized `excluded` list in `policy/public-tf-producers.json`. Keep all actual producers, tracking issues, CI markers and the fail-closed inventory audit unchanged. Observable RED is the actual failed GitHub Action before implementation. Exact-head GREEN requires passing the same *live* owner inventory plus full CI, independent adverse review of this specific repository’s actual README and minimal diff, then guarded merge. Do not claim the Syriac editor is a TF consumer.
