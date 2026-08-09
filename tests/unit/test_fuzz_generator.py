# tests/unit/test_fuzz_generator.py
"""
Unit tests for the fuzz test generator pipeline.
Tests run_fuzz_generator, validate_generated_inputs, and build_combined_test_suite.
"""
import pytest
from unittest.mock import patch, MagicMock
import subprocess

from synapse.vjs import (
    run_fuzz_generator,
    validate_generated_inputs,
    build_combined_test_suite,
)


class TestRunFuzzGenerator:

    def test_simple_generator(self):
        """A simple generator that prints 'hello' should produce N identical inputs."""
        gen_script = "print('hello')"
        inputs = run_fuzz_generator(gen_script, count=3, timeout_per_run=5)
        assert len(inputs) == 3
        assert all(x == "hello" for x in inputs)

    def test_random_generator(self):
        """A generator with randomness should produce mostly unique inputs."""
        gen_script = "import random; print(random.randint(1, 1000000))"
        inputs = run_fuzz_generator(gen_script, count=10, timeout_per_run=5)
        assert len(inputs) == 10
        # At least 8/10 should be unique (extremely unlikely to collide)
        assert len(set(inputs)) >= 8

    def test_failing_generator_returns_empty(self):
        """A generator that always crashes should return []."""
        gen_script = "import sys; sys.exit(1)"
        inputs = run_fuzz_generator(gen_script, count=3, timeout_per_run=5)
        assert inputs == []

    def test_empty_output_skipped(self):
        """A generator that prints nothing should not produce inputs."""
        gen_script = "pass"
        inputs = run_fuzz_generator(gen_script, count=3, timeout_per_run=5)
        assert inputs == []

    def test_timeout_handled(self):
        """A generator that hangs should not crash, just skip that run."""
        gen_script = "import time; time.sleep(100)"
        inputs = run_fuzz_generator(gen_script, count=2, timeout_per_run=1)
        assert inputs == []


class TestBuildCombinedTestSuite:

    def test_merge_pretests_and_generated(self):
        pretests = [{'input': '1', 'output': '2'}]
        generated = [{'input': '3', 'output': '4'}]
        result = build_combined_test_suite(pretests, generated)
        assert len(result) == 2

    def test_deduplicates_by_input(self):
        pretests = [{'input': '1', 'output': '2'}]
        generated = [{'input': '1', 'output': '2'}]  # Same input
        result = build_combined_test_suite(pretests, generated)
        assert len(result) == 1

    def test_pretests_take_priority(self):
        pretests = [{'input': '1', 'output': 'pretest_output'}]
        generated = [{'input': '1', 'output': 'gen_output'}]
        result = build_combined_test_suite(pretests, generated)
        assert len(result) == 1
        assert result[0]['output'] == 'pretest_output'

    def test_empty_pretests(self):
        result = build_combined_test_suite([], [{'input': '3', 'output': '4'}])
        assert len(result) == 1

    def test_empty_generated(self):
        result = build_combined_test_suite([{'input': '1', 'output': '2'}], [])
        assert len(result) == 1

    def test_both_empty(self):
        result = build_combined_test_suite([], [])
        assert result == []

    def test_multiple_unique(self):
        pretests = [{'input': str(i), 'output': str(i * 2)} for i in range(5)]
        generated = [{'input': str(i + 10), 'output': str((i + 10) * 2)} for i in range(5)]
        result = build_combined_test_suite(pretests, generated)
        assert len(result) == 10


class TestValidateGeneratedInputs:

    def test_empty_inputs_returns_empty(self):
        result = validate_generated_inputs([], ['/fake/oracle'])
        assert result == []

    def test_empty_oracles_returns_empty(self):
        result = validate_generated_inputs(['input1'], [])
        assert result == []
