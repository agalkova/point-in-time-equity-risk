from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from risk_managed_momentum.operations.cloud import build_run_bundle, publish_bundle


class MissingObject(Exception):
    def __init__(self) -> None:
        self.response = {"Error": {"Code": "NoSuchKey"}}


class FakeObjectStore:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, io.BytesIO]:
        try:
            content = self.objects[(Bucket, Key)]
        except KeyError as error:
            raise MissingObject() from error
        return {"Body": io.BytesIO(content)}

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: dict[str, str],
    ) -> dict[str, str]:
        del ContentType, Metadata
        self.objects[(Bucket, Key)] = Body
        return {"ETag": "fake"}


class CloudJobTests(unittest.TestCase):
    def summary(self) -> dict[str, object]:
        return {
            "source": "deterministic synthetic data",
            "research_claim_supported": False,
            "test_events": 4,
            "test_observations": 20,
            "test_roc_auc": 0.7,
        }

    def test_bundle_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            arguments = {
                "run_id": "synthetic-20261029-abc-1234",
                "run_date": "2026-10-29",
                "summary": self.summary(),
                "input_sha256": "a" * 64,
                "commit_sha": "b" * 40,
                "image_uri": "example/image:sha",
            }
            first, reused = build_run_bundle(root, **arguments)
            second, reused_second = build_run_bundle(root, **arguments)
            self.assertFalse(reused)
            self.assertTrue(reused_second)
            self.assertEqual(first, second)

    def test_changed_retry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build_run_bundle(
                root,
                run_id="same-run",
                run_date="2026-10-29",
                summary=self.summary(),
                input_sha256="a" * 64,
                commit_sha="b" * 40,
                image_uri="example/image:sha",
            )
            changed = self.summary()
            changed["test_roc_auc"] = 0.9
            with self.assertRaises(FileExistsError):
                build_run_bundle(
                    root,
                    run_id="same-run",
                    run_date="2026-10-29",
                    summary=changed,
                    input_sha256="a" * 64,
                    commit_sha="b" * 40,
                    image_uri="example/image:sha",
                )

    def test_s3_publication_verifies_immutable_run_objects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle, _ = build_run_bundle(
                Path(directory),
                run_id="synthetic-run",
                run_date="2026-10-29",
                summary=self.summary(),
                input_sha256="a" * 64,
                commit_sha="b" * 40,
                image_uri="example/image:sha",
            )
            store = FakeObjectStore()
            first = publish_bundle(store, bucket="bucket", prefix="demo", bundle=bundle)
            second = publish_bundle(store, bucket="bucket", prefix="demo", bundle=bundle)
            self.assertEqual(first, second)
            self.assertIn(("bucket", "demo/status/latest.json"), store.objects)


if __name__ == "__main__":
    unittest.main()
