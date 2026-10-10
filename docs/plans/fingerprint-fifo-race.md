# Plan: nonblocking POSIX open in raw artifact fingerprinting

Issue: #24

## RED-first regression

Use a real temporary regular source file and monkeypatch the `os.open` boundary to replace the regular source with an actual FIFO **after** `os.scandir` has completed, just before open. The intercepted `os.open` asserts the `O_NONBLOCK` flag **before** replacing the file or invoking the real syscall: on old code this fails quickly rather than hanging. On fixed code the actual nonblocking FIFO open returns immediately, `fstat` rejects the nonregular fd, and the user sees `FingerprintError`. Skip on non-POSIX platforms without `mkfifo`.

## Production change

Use the existing no-follow and binary flags, plus `O_NONBLOCK` on POSIX. Fail closed if this flag cannot be provided. Preserve the `fstat` regular-file check before stream reads; no behavioral change for normal shipped files.

## Follow-up quality gates

Run existing deterministic raw-byte and aggregate hash oracle tests, FIFO/symlink tests, Ruff, strict mypy and pytest across Python 3.11–3.14 on exact PR head. Independent review should explicitly check that the test cannot hang without the fix and that normal regular-file I/O remains unchanged.
