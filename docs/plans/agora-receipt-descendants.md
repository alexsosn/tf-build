# Issue #96 implementation plan

1. Commit research and plan before code (this branch).
2. Add a deterministic failed test with `agora_output_path(root, "agora-materialization.json/nested.tf")`, assert `AgoraOutputError` and that the root stays empty; retain positive nested `tf/agora-materialization.json` case.
3. Run tests on unchanged production; record observed RED and distinguish remote CI failures from local reproductions.
4. In `_relative_path`, compute validated POSIX path components once and reject when component zero is reserved. Keep all other validation conditions and no-clobber ownership as-is.
5. Full matrix Ruff/mypy/pytest + wheel distribution and public producer audit on frozen final head. Review exact diff skeptically against real Agora `_write_provenance` behavior; no merge with failing or pending checks.
6. Close issue on merge; keep release issue #60 and ORAEC consumer #53 open.
