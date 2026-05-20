import unittest

from fastapi import HTTPException

from main import _extract_pr_info, _parse_and_validate_webhook_payload


class WebhookPayloadTests(unittest.TestCase):
    def test_parse_payload_rejects_invalid_json(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _parse_and_validate_webhook_payload(b"{invalid json")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Malformed JSON payload")

    def test_parse_payload_rejects_non_object(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _parse_and_validate_webhook_payload(b"[1, 2]")

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail, "Webhook payload must be a JSON object"
        )

    def test_parse_payload_accepts_object(self) -> None:
        payload = _parse_and_validate_webhook_payload(b'{"action": "opened"}')
        self.assertEqual(payload, {"action": "opened"})


class PullRequestInfoTests(unittest.TestCase):
    def test_extract_pr_info_requires_repo_and_pr(self) -> None:
        with self.assertRaises(HTTPException) as context:
            _extract_pr_info({})

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail, "Invalid repository or pull_request format"
        )

    def test_extract_pr_info_validates_full_name_type(self) -> None:
        payload = {"repository": {"full_name": 123}, "pull_request": {"number": 1}}
        with self.assertRaises(HTTPException) as context:
            _extract_pr_info(payload)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail, "Repository full_name must be a string"
        )

    def test_extract_pr_info_validates_full_name_empty(self) -> None:
        payload = {"repository": {"full_name": "  "}, "pull_request": {"number": 1}}
        with self.assertRaises(HTTPException) as context:
            _extract_pr_info(payload)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail, "Repository full_name cannot be empty"
        )

    def test_extract_pr_info_validates_pr_number(self) -> None:
        payload = {
            "repository": {"full_name": "octo/repo"},
            "pull_request": {"number": "1"},
        }
        with self.assertRaises(HTTPException) as context:
            _extract_pr_info(payload)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Invalid pull request number")

    def test_extract_pr_info_requires_positive_pr_number(self) -> None:
        payload = {
            "repository": {"full_name": "octo/repo"},
            "pull_request": {"number": 0},
        }
        with self.assertRaises(HTTPException) as context:
            _extract_pr_info(payload)

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(
            context.exception.detail, "Pull request number must be positive"
        )

    def test_extract_pr_info_strips_full_name(self) -> None:
        payload = {
            "repository": {"full_name": "  octo/repo  "},
            "pull_request": {"number": 7},
        }
        repo_full_name, pr_number = _extract_pr_info(payload)
        self.assertEqual(repo_full_name, "octo/repo")
        self.assertEqual(pr_number, 7)

    def test_extract_pr_info_returns_values(self) -> None:
        payload = {
            "repository": {"full_name": "octo/repo"},
            "pull_request": {"number": 42},
        }
        repo_full_name, pr_number = _extract_pr_info(payload)
        self.assertEqual(repo_full_name, "octo/repo")
        self.assertEqual(pr_number, 42)


if __name__ == "__main__":
    unittest.main()
