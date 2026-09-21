import unittest
from unittest.mock import patch

from agents import lessons


class _Result:
    def __init__(self, rows=None):
        self.rows = rows or []

    def fetchall(self):
        return self.rows


class _Connection:
    def __init__(self, rows=None, execute_error=None):
        self.rows = rows or []
        self.execute_error = execute_error
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, query, params):
        self.calls.append((query, params))
        if self.execute_error:
            raise self.execute_error
        return _Result(self.rows)


class LessonsTests(unittest.TestCase):
    def test_get_relevant_lessons_prefers_platform_and_limits_results(self) -> None:
        connection = _Connection(rows=[{"note": "Use a calmer CTA"}, {"note": "Avoid absolutes"}])

        with patch.object(lessons, "get_connection", return_value=connection):
            result = lessons.get_relevant_lessons("jade", "linkedin", limit=2)

        self.assertEqual(result, ["Use a calmer CTA", "Avoid absolutes"])
        query, params = connection.calls[0]
        self.assertIn("platform = %s or platform is null", query)
        self.assertIn("case when platform = %s then 0 else 1 end", query)
        self.assertIn("created_at desc", query)
        self.assertEqual(params, ("jade", "linkedin", "linkedin", 2))

    def test_get_relevant_lessons_returns_empty_on_db_failure(self) -> None:
        connection = _Connection(execute_error=RuntimeError("database unavailable"))

        with patch.object(lessons, "get_connection", return_value=connection):
            result = lessons.get_relevant_lessons("jade", "linkedin")

        self.assertEqual(result, [])

    def test_non_positive_limit_skips_database(self) -> None:
        with patch.object(lessons, "get_connection") as get_connection:
            self.assertEqual(lessons.get_relevant_lessons("jade", "linkedin", limit=0), [])

        get_connection.assert_not_called()

    def test_record_lesson_coalesces_empty_note_and_reason(self) -> None:
        connection = _Connection()

        with patch.object(lessons, "get_connection", return_value=connection):
            lessons.record_lesson(
                asset_id="asset-1",
                reason_tag="",
                note="",
                original="Original copy",
                edited=None,
                brand_id="jade",
                platform="linkedin",
            )

        _, params = connection.calls[0]
        self.assertEqual(
            params,
            (
                "jade",
                "linkedin",
                "OTHER",
                "Reviewer correction",
                "Original copy",
                None,
                "asset-1",
            ),
        )

    def test_record_lesson_uses_reason_tag_when_note_is_empty(self) -> None:
        connection = _Connection()

        with patch.object(lessons, "get_connection", return_value=connection):
            lessons.record_lesson(
                "asset-1",
                "TOO_SALESY",
                "",
                "Original copy",
                None,
                "jade",
                "linkedin",
            )

        self.assertEqual(connection.calls[0][1][2:4], ("TOO_SALESY", "TOO_SALESY"))

    def test_record_lesson_preserves_write_errors(self) -> None:
        connection = _Connection(execute_error=RuntimeError("write failed"))

        with patch.object(lessons, "get_connection", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "write failed"):
                lessons.record_lesson(
                    "asset-1",
                    "UNSUPPORTED_CLAIM",
                    "Use qualified wording",
                    "Original",
                    "Edited",
                    "jade",
                    "linkedin",
                )


if __name__ == "__main__":
    unittest.main()
