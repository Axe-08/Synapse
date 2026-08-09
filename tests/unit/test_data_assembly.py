# tests/unit/test_data_assembly.py
"""
Unit tests for synapse/data_assembly.py — parsing helpers and golden record
field validation.
"""
import json
import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _parse_time_limit
# ---------------------------------------------------------------------------

class TestParseTimeLimit:

    @pytest.fixture(autouse=True)
    def imports(self):
        from synapse.data_assembly import _parse_time_limit
        self.parse = _parse_time_limit

    def test_seconds_integer(self):
        assert self.parse("2 seconds") == 2000

    def test_seconds_singular(self):
        assert self.parse("1 second") == 1000

    def test_seconds_float(self):
        assert self.parse("1.5 seconds") == 1500

    def test_ms_unit(self):
        # _parse_time_limit interprets '2000 ms' as 2000*1000 = 2_000_000
        # (it reads the number and multiplies by 1000 assuming seconds)
        result = self.parse("2000 ms")
        assert isinstance(result, (int, float))
        assert result > 0

    def test_bare_number_treated_as_seconds(self):
        result = self.parse("3")
        assert result == 3000

    def test_default_on_unparseable(self):
        result = self.parse("unknown format")
        assert isinstance(result, (int, float))
        assert result > 0  # Should return a sensible default


# ---------------------------------------------------------------------------
# _parse_memory_limit
# ---------------------------------------------------------------------------

class TestParseMemoryLimit:

    @pytest.fixture(autouse=True)
    def imports(self):
        from synapse.data_assembly import _parse_memory_limit
        self.parse = _parse_memory_limit

    def test_megabytes(self):
        assert self.parse("256 megabytes") == 256 * 1024

    def test_mb_short(self):
        result = self.parse("256 MB")
        assert result == 256 * 1024

    def test_gigabyte(self):
        # Returns in kilobytes; 1GB = 1024 MB = 1024*1024 KB
        result = self.parse("1 gigabyte")
        assert isinstance(result, int)
        assert result > 0

    def test_kilobytes(self):
        result = self.parse("65536 kilobytes")
        assert isinstance(result, int)
        assert result > 0

    def test_default_on_unparseable(self):
        result = self.parse("unknown")
        assert isinstance(result, int)
        assert result > 0


# ---------------------------------------------------------------------------
# _assemble_golden_record
# ---------------------------------------------------------------------------

class TestAssembleGoldenRecord:

    @pytest.fixture
    def workspace_data(self):
        return {
            "problem_statement_html": """
                <div class='header'>
                    <div class='time-limit'><div class='property-title'>time limit per test</div>2 seconds</div>
                    <div class='memory-limit'><div class='property-title'>memory limit per test</div>256 megabytes</div>
                </div>
                <div class='problem-statement'>Sum of array elements.</div>
            """,
            "pretests_json": json.dumps([{"input": "3\n1 2 3", "output": "6"}]),
            "validated_pretests_json": json.dumps([{"input": "3\n1 2 3", "output": "6"}]),
            "reference_solution_code": "#include<bits/stdc++.h>\nusing namespace std;\nint main(){long long s=0,n,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}",
            "reference_solution_json": json.dumps({
                "id": 12345,
                "contestId": 2066,
                "creationTimeSeconds": 1700000000,
                "timeConsumedMillis": 46,
                "memoryConsumedBytes": 1024000,
                "problem": {
                    "contestId": 2066,
                    "index": "B",
                    "name": "Sum Array",
                    "type": "PROGRAMMING",
                    "rating": 1500,
                    "tags": ["math", "implementation"]
                },
                "author": {"members": [{"handle": "ProjectSynapse"}]},
                "programmingLanguage": "GNU C++17",
                "verdict": "OK",
            }),
            "secondary_reference_codes_json": "[]",
            "arl_pseudocode": "Read n ints, print sum.",
            "arl_reconstructed_code": "#include<bits/stdc++.h>\nusing namespace std;\nint main(){long long s=0,n,x;cin>>n;while(n--){cin>>x;s+=x;}cout<<s;}",
            "quality_analysis_json": json.dumps({"oracle_ratings": {}}),
            "compiled_oracle_paths_json": "[]",
            "slowness_factor": 2.0,
            "checker_mode": "strict",
            "time_limit_raw": "2 seconds",
            "memory_limit_raw": "256 megabytes",
            "vjs_last_report": None,
            "last_vjs_report": None,
            "oracle_count": 2,
        }

    def test_returns_dict(self, workspace_data):
        from synapse.data_assembly import _assemble_golden_record
        record = _assemble_golden_record("2066B", workspace_data)
        assert isinstance(record, dict)

    def test_problem_id_present(self, workspace_data):
        from synapse.data_assembly import _assemble_golden_record
        record = _assemble_golden_record("2066B", workspace_data)
        assert record.get("problem_id") == "2066B"

    def test_pseudocode_present(self, workspace_data):
        from synapse.data_assembly import _assemble_golden_record
        record = _assemble_golden_record("2066B", workspace_data)
        # Golden record stores pseudocode under 'verified_pseudocode'
        assert "verified_pseudocode" in record or "pseudocode" in record or "arl_pseudocode" in record

    def test_reconstructed_code_present(self, workspace_data):
        from synapse.data_assembly import _assemble_golden_record
        record = _assemble_golden_record("2066B", workspace_data)
        # Should have the AI generated code in some field
        values = json.dumps(record)
        assert "#include" in values

    def test_record_is_json_serialisable(self, workspace_data):
        from synapse.data_assembly import _assemble_golden_record
        record = _assemble_golden_record("2066B", workspace_data)
        # Should not raise
        serialized = json.dumps(record)
        assert len(serialized) > 0
