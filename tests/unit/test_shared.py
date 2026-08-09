# tests/unit/test_shared.py
"""
Unit tests for synapse/workers/_shared.py — _voter and _score_code_quality.
These are pure functions with no external dependencies.
"""
import pytest
from synapse.workers._shared import _voter, _score_code_quality


# ---------------------------------------------------------------------------
# _voter
# ---------------------------------------------------------------------------

class TestVoter:

    def test_empty_list_returns_none(self):
        assert _voter([]) is None

    def test_single_item_is_majority(self):
        assert _voter(["42"]) == "42"

    def test_clear_majority(self):
        outputs = ["10", "10", "10", "5", "3"]
        assert _voter(outputs) == "10"

    def test_exact_majority_boundary(self):
        # 3 out of 5 = 60% → majority
        outputs = ["A", "A", "A", "B", "B"]
        assert _voter(outputs) == "A"

    def test_hung_jury_even_split(self):
        # 2 out of 4 = 50% → NOT majority (needs > 50%)
        outputs = ["A", "A", "B", "B"]
        assert _voter(outputs) is None

    def test_hung_jury_three_way(self):
        outputs = ["A", "B", "C"]
        assert _voter(outputs) is None

    def test_all_same(self):
        outputs = ["result\n42"] * 5
        assert _voter(outputs) == "result\n42"

    def test_multiline_output_preserved(self):
        outputs = ["1\n2\n3", "1\n2\n3", "0"]
        assert _voter(outputs) == "1\n2\n3"

    def test_whitespace_counts_as_distinct(self):
        # "42" and "42 " are different strings
        outputs = ["42", "42", "42 "]
        assert _voter(outputs) == "42"

    def test_single_minority_runtime_error(self):
        outputs = ["10", "10", "ORACLE_RUNTIME_ERROR_CODE_1"]
        assert _voter(outputs) == "10"


# ---------------------------------------------------------------------------
# _score_code_quality
# ---------------------------------------------------------------------------

class TestScoreCodeQuality:

    def test_empty_string_scores_zero(self):
        assert _score_code_quality("") == 0

    def test_clean_code_low_score(self):
        code = '#include<iostream>\nusing namespace std;\nint main(){int x;cin>>x;cout<<x;}'
        score = _score_code_quality(code)
        assert score >= 0
        # 1 include = score of 1
        assert score == 1

    def test_define_penalised_heavily(self):
        code = '#define int long long\n#define rep(i,n) for(int i=0;i<n;i++)'
        score = _score_code_quality(code)
        # 2 defines × 5 = 10
        assert score == 10

    def test_scanf_printf_penalised(self):
        code = 'scanf("%d",&n);\nprintf("%d\\n",ans);'
        score = _score_code_quality(code)
        # 1 scanf × 2 + 1 printf × 2 = 4
        assert score == 4

    def test_multiple_includes_accumulate(self):
        code = '#include<bits/stdc++.h>\n#include<cstring>'
        score = _score_code_quality(code)
        assert score == 2  # 2 includes × 1

    def test_messy_competitive_code_scores_high(self):
        messy = (
            '#define int long long\n'
            '#define rep(i,n) for(int i=0;i<n;i++)\n'
            '#include<bits/stdc++.h>\n'
            'scanf("%d %d",&n,&m);\n'
            'printf("%lld\\n",ans);\n'
        )
        score = _score_code_quality(messy)
        # 2 defines×5 + 1 include + 1 scanf×2 + 1 printf×2 = 15
        assert score == 15

    def test_lower_score_is_better(self):
        clean = '#include<iostream>\nusing namespace std;\nint main(){}'
        messy = '#define ll long long\n#define rep(i,n) for(int i=0;i<n;i++)'
        assert _score_code_quality(clean) < _score_code_quality(messy)
