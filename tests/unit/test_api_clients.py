# tests/unit/test_api_clients.py
"""
Unit tests for api_clients: prompt construction, code sanitization, and model config.
"""
import pytest
from synapse.api_clients import (
    _preprocess_code_for_llm,
    _sanitize_cpp_code,
    _sanitize_python_code,
    _estimate_tokens,
    _CLASS_INSTRUCTIONS,
    GEMINI_MODEL_NAME,
    GROQ_MODEL_NAME,
    GROQ_FALLBACK_MODEL,
    GROQ_IMPLEMENTER_PROMPT,
    GEMINI_FUZZ_GENERATOR_PROMPT,
)


class TestModelConfig:

    def test_gemini_model_set(self):
        assert 'gemini' in GEMINI_MODEL_NAME.lower()

    def test_groq_primary_model(self):
        assert 'qwen' in GROQ_MODEL_NAME.lower() or 'qwq' in GROQ_MODEL_NAME.lower()

    def test_groq_fallback_model(self):
        assert 'llama' in GROQ_FALLBACK_MODEL.lower()


class TestPreprocessCode:

    def test_removes_includes(self):
        code = '#include <bits/stdc++.h>\nint main(){}'
        result = _preprocess_code_for_llm(code)
        assert '#include' not in result
        assert 'int main(){}' in result

    def test_removes_using_namespace(self):
        code = 'using namespace std;\nint x = 5;'
        result = _preprocess_code_for_llm(code)
        assert 'using namespace' not in result

    def test_removes_comments(self):
        code = '// This is a comment\nint x = 5; /* block */\nint y = 10;'
        result = _preprocess_code_for_llm(code)
        assert 'This is a comment' not in result
        assert 'block' not in result

    def test_removes_ios_base(self):
        code = 'ios_base::sync_with_stdio(false);\ncin.tie(NULL);\nint n;'
        result = _preprocess_code_for_llm(code)
        assert 'ios_base' not in result
        assert 'cin.tie' not in result


class TestSanitizeCpp:

    def test_strips_markdown_cpp(self):
        raw = '```cpp\nint main(){}\n```'
        assert _sanitize_cpp_code(raw) == 'int main(){}'

    def test_strips_markdown_plain(self):
        raw = '```\nint main(){}\n```'
        assert _sanitize_cpp_code(raw) == 'int main(){}'

    def test_no_markdown(self):
        raw = 'int main(){}'
        assert _sanitize_cpp_code(raw) == 'int main(){}'


class TestSanitizePython:

    def test_strips_python_block(self):
        raw = '```python\nimport random\nprint(1)\n```'
        assert _sanitize_python_code(raw) == 'import random\nprint(1)'

    def test_strips_py_block(self):
        raw = '```py\nprint(1)\n```'
        assert _sanitize_python_code(raw) == 'print(1)'

    def test_no_markdown(self):
        raw = 'print(1)'
        assert _sanitize_python_code(raw) == 'print(1)'


class TestClassInstructions:

    def test_standard_is_empty(self):
        assert _CLASS_INSTRUCTIONS['standard'] == ''

    def test_interactive_mentions_flush(self):
        assert 'flush' in _CLASS_INSTRUCTIONS['interactive'].lower()
        assert 'endl' in _CLASS_INSTRUCTIONS['interactive'].lower()

    def test_special_judge_mentions_valid(self):
        assert 'valid' in _CLASS_INSTRUCTIONS['special_judge'].lower()

    def test_constructive_mentions_construct(self):
        assert 'construct' in _CLASS_INSTRUCTIONS['constructive'].lower()


class TestPromptTemplates:

    def test_implementer_prompt_has_placeholders(self):
        assert '{problem_html}' in GROQ_IMPLEMENTER_PROMPT
        assert '{pseudocode}' in GROQ_IMPLEMENTER_PROMPT
        assert '{vjs_report}' in GROQ_IMPLEMENTER_PROMPT
        assert '{class_instructions}' in GROQ_IMPLEMENTER_PROMPT

    def test_fuzz_prompt_has_placeholders(self):
        assert '{problem_html}' in GEMINI_FUZZ_GENERATOR_PROMPT
        assert '{time_limit}' in GEMINI_FUZZ_GENERATOR_PROMPT
        assert '{memory_limit}' in GEMINI_FUZZ_GENERATOR_PROMPT


class TestEstimateTokens:

    def test_rough_estimate(self):
        text = "a" * 400
        assert _estimate_tokens(text) == 100

    def test_empty_string(self):
        assert _estimate_tokens("") == 0
