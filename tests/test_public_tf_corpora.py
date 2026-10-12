"""Offline RED-first policy checks for portfolio TF corpus coverage."""

import unittest
from urllib.error import HTTPError
from scripts.audit_public_tf_corpora import IMPLEMENTED, TRACKED, audit, is_corpus_builder


def corpus_repos():
    return [{"name": name, "fork": False, "private": False}
            for name in sorted(IMPLEMENTED | TRACKED.keys())]


def fake_api(path):
    if path.endswith("/contents/.github/workflows"):
        return [{"name": "ci.yml", "type": "file"}]
    return {"state": "open"}


class CorpusAuditTests(unittest.TestCase):
    def test_known_repos_are_covered(self):
        self.assertEqual([], audit(corpus_repos(), fake_api))

    def test_new_public_tf_converter_must_be_classified(self):
        repos = corpus_repos() + [{"name": "New-Corpus-TF", "private": False, "fork": False}]
        self.assertTrue(any("New-Corpus-TF" in e for e in audit(repos, fake_api)))

    def test_forks_private_non_corpora_not_included(self):
        self.assertFalse(is_corpus_builder({"name": "Foreign-TF", "fork": True, "private": False}))
        self.assertFalse(is_corpus_builder({"name": "Private-TF", "fork": False, "private": True}))
        self.assertFalse(is_corpus_builder({"name": "tf-build", "fork": False, "private": False}))

    def test_closed_tracking_issue_fails(self):
        def closed(path):
            return {"state": "closed"} if "/issues/" in path else fake_api(path)
        self.assertTrue(any("no longer an open" in e for e in audit(corpus_repos(), closed)))

    def test_closed_pull_request_is_not_an_issue(self):
        def pr(path):
            return {"state": "open", "pull_request": {}} if "/issues/" in path else fake_api(path)
        self.assertTrue(any("open implementation issue" in e for e in audit(corpus_repos(), pr)))

    def test_missing_actions_ci_fails(self):
        def missing(path):
            return [] if path.endswith("/workflows") else fake_api(path)
        self.assertTrue(any("no GitHub Actions workflow" in e for e in audit(corpus_repos(), missing)))

    def test_transient_api_error_fails_closed(self):
        def failing(path):
            if "/issues/" in path:
                raise HTTPError(path, 403, "rate-limited", {}, None)
            return fake_api(path)
        self.assertTrue(any("cannot verify tracking issue" in e for e in audit(corpus_repos(), failing)))

    def test_removed_repository_cannot_stay_classified(self):
        self.assertTrue(any("missing from public non-fork" in e for e in audit([], fake_api)))


if __name__ == "__main__":
    unittest.main()
