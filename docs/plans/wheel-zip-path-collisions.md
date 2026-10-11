# Plan: reject ZIP member file/directory collisions (#66)

1. Write deterministic pytest fixtures producing the actual conflicting ZIP layouts; add tests for same-path file vs directory, file-as-ancestor (both orders), and `.dist-info` equivalents. Add a control with explicit directory and child file that remains accepted.
2. Commit RED tests separately from implementation. Run affected tests on exact test-only branch and preserve the observed failure (CI acceptable if local environment lacks development dependencies).
3. Update `_package_payload` only: track normalized explicit member paths, explicit files, and implicit parent directories. For each member reject a duplicate normalized path, a previously seen ancestor file, and files on paths already required as directories. Keep complexity proportional to total ZIP path components and payload bytes; never extract or execute.
4. Run focused + full tests, static checks, CI Python matrix and distribution gates; independently inspect final patch for both orderings and legitimate directory layouts.
5. Merge after exact-head green plus independent adversarial review; leave release issue #60 pending actual durable publication.
