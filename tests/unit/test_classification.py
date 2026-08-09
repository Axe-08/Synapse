# tests/unit/test_classification.py
"""
Unit tests for problem classification and routing logic.
"""
import pytest
from synapse.scraper import classify_problem


class TestClassifyProblemInteractive:
    """Tests for interactive problem detection."""

    def test_interactive_from_cf_type(self):
        """CF API type=INTERACTIVE should classify as interactive."""
        assert classify_problem(problem_type="INTERACTIVE") == "interactive"

    def test_interactive_from_cf_type_case_insensitive(self):
        assert classify_problem(problem_type="interactive") == "interactive"

    def test_interactive_from_statement_interaction_protocol(self):
        html = "<p>This is an <b>interactive</b> problem. Interaction protocol: ...</p>"
        assert classify_problem(statement_html=html) == "interactive"

    def test_interactive_from_statement_interactor(self):
        html = "<p>Note: this problem uses an interactor.</p>"
        assert classify_problem(statement_html=html) == "interactive"

    def test_interactive_from_tags(self):
        assert classify_problem(tags=["dp", "interactive"]) == "interactive"


class TestClassifyProblemSpecialJudge:
    """Tests for special-judge problem detection."""

    def test_special_judge_from_tags(self):
        assert classify_problem(tags=["math", "special judge"]) == "special_judge"

    def test_special_judge_from_tags_special_only(self):
        assert classify_problem(tags=["special"]) == "special_judge"

    def test_special_judge_from_statement_any_valid(self):
        html = "<p>If there are multiple answers, you may print any of them.</p>"
        assert classify_problem(statement_html=html) == "special_judge"

    def test_special_judge_from_statement_print_any(self):
        html = "<p>If the answer is not unique, print any of them.</p>"
        assert classify_problem(statement_html=html) == "special_judge"

    def test_special_judge_from_statement_any_valid_answer(self):
        html = "<p>Any valid answer will be accepted.</p>"
        assert classify_problem(statement_html=html) == "special_judge"

    def test_special_judge_from_statement_multiple(self):
        html = "<p>If there are multiple valid solutions, output any.</p>"
        assert classify_problem(statement_html=html) == "special_judge"

    def test_special_judge_from_statement_several(self):
        html = "<p>If there are several answers, print any of them.</p>"
        assert classify_problem(statement_html=html) == "special_judge"


class TestClassifyProblemConstructive:
    """Tests for constructive problem detection."""

    def test_constructive_from_tags(self):
        assert classify_problem(tags=["constructive algorithms", "greedy"]) == "constructive"

    def test_constructive_from_statement_construct(self):
        html = "<p>Construct a permutation of length n such that...</p>"
        assert classify_problem(statement_html=html) == "constructive"

    def test_constructive_from_statement_find_any(self):
        html = "<p>Find any valid assignment of values.</p>"
        assert classify_problem(statement_html=html) == "constructive"

    def test_constructive_from_statement_output_any_valid(self):
        html = "<p>Output any valid sequence.</p>"
        assert classify_problem(statement_html=html) == "constructive"


class TestClassifyProblemStandard:
    """Tests for standard (default) classification."""

    def test_standard_default(self):
        assert classify_problem() == "standard"

    def test_standard_with_normal_tags(self):
        assert classify_problem(tags=["dp", "math", "number theory"]) == "standard"

    def test_standard_with_normal_statement(self):
        html = "<p>Print the maximum sum of the subarray.</p>"
        assert classify_problem(statement_html=html) == "standard"

    def test_standard_programming_type(self):
        assert classify_problem(problem_type="PROGRAMMING") == "standard"


class TestClassifyProblemPriority:
    """Tests for classification priority: interactive > special_judge > constructive."""

    def test_interactive_beats_special_judge(self):
        """If both interactive and special judge signals, interactive wins."""
        result = classify_problem(
            problem_type="INTERACTIVE",
            tags=["special judge"],
        )
        assert result == "interactive"

    def test_special_judge_beats_constructive(self):
        """If both special judge and constructive signals, special_judge wins."""
        result = classify_problem(
            tags=["special judge", "constructive algorithms"],
        )
        assert result == "special_judge"


class TestClassifyProblemEdgeCases:
    """Edge cases."""

    def test_empty_tags_none(self):
        assert classify_problem(tags=None) == "standard"

    def test_empty_statement(self):
        assert classify_problem(statement_html="") == "standard"

    def test_case_insensitive_statement(self):
        html = "<p>YOU MAY PRINT ANY of the valid answers.</p>"
        assert classify_problem(statement_html=html) == "special_judge"


class TestRoutingByProblemClass:
    """Tests for problem routing based on classification."""

    def test_get_next_jobs_includes_problem_class(self, tmp_progress_db):
        """get_next_jobs should return problem_class in job dict."""
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating, problem_class) VALUES (?, ?, ?, ?)",
                ("1234A", "pending_analysis", 1500, "interactive"),
            )
            conn.commit()
        jobs = db.get_next_jobs("pending_analysis", limit=1)
        assert len(jobs) == 1
        assert jobs[0]["problem_class"] == "interactive"

    def test_get_next_jobs_default_class_is_standard(self, tmp_progress_db):
        """Problems without explicit problem_class default to 'standard'."""
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating) VALUES (?, ?, ?)",
                ("1234B", "pending_analysis", 800),
            )
            conn.commit()
        jobs = db.get_next_jobs("pending_analysis", limit=1)
        assert jobs[0]["problem_class"] == "standard"

    def test_transition_to_pending_cf_submission(self, tmp_progress_db):
        """transition_to_pending_cf_submission should set correct status."""
        import synapse.database as db
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO problems (id, status, rating) VALUES (?, ?, ?)",
                ("999A", "in_progress_implementation", 1200),
            )
            conn.commit()
        db.transition_to_pending_cf_submission("999A")
        with db._get_db_connection(db.PROGRESS_DB_PATH) as conn:
            row = conn.execute("SELECT status FROM problems WHERE id = ?", ("999A",)).fetchone()
        assert row[0] == "pending_cf_submission"
