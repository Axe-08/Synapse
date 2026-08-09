# tests/unit/test_key_manager.py
"""
Unit tests for synapse/key_manager.py.

KeyManager.get_key() returns a ManagedKey dataclass object.
Access the key string via managed_key.key_string.
Return keys with release_key(key, outcome, tokens_used=0) where outcome is a KeyStatus enum.
"""
import pytest
from synapse.key_manager import KeyManager, KeyStatus

pytestmark = pytest.mark.unit


@pytest.fixture
def km():
    """KeyManager with 3 fake keys."""
    return KeyManager(["key_A", "key_B", "key_C"], service_name="TEST")


class TestKeyManagerBasic:

    def test_get_key_returns_managed_key_object(self, km):
        key = km.get_key()
        assert key is not None
        assert hasattr(key, 'key_string')

    def test_get_key_returns_valid_key_string(self, km):
        key = km.get_key()
        assert key.key_string in ("key_A", "key_B", "key_C")

    def test_single_key_returns_non_none(self):
        km_single = KeyManager(["only_key"], service_name="TEST")
        key = km_single.get_key()
        assert key is not None
        assert key.key_string == "only_key"

    def test_round_robin_cycles_through_keys(self, km):
        """Release each key after use so the next call can get a different one."""
        seen = set()
        for _ in range(3):
            key = km.get_key()
            assert key is not None
            seen.add(key.key_string)
            km.release_key(key, KeyStatus.AVAILABLE)
        assert seen == {"key_A", "key_B", "key_C"}

    def test_get_key_marks_key_as_in_use(self, km):
        key = km.get_key()
        assert key is not None
        assert key.status == KeyStatus.IN_USE
        km.release_key(key, KeyStatus.AVAILABLE)


class TestReleaseKey:

    def test_release_with_success_does_not_raise(self, km):
        key = km.get_key()
        try:
            km.release_key(key, KeyStatus.AVAILABLE)
        except Exception as e:
            pytest.fail(f"release_key raised: {e}")

    def test_release_with_rate_limited_marks_key(self, km):
        key = km.get_key()
        km.release_key(key, KeyStatus.RATE_LIMITED)
        # The key should now be rate-limited (cooldown set)
        assert key.cooldown_until > 0

    def test_released_key_becomes_available_again(self, km):
        key1 = km.get_key()
        km.release_key(key1, KeyStatus.AVAILABLE)
        key2 = km.get_key()
        assert key2 is not None
        km.release_key(key2, KeyStatus.AVAILABLE)

    def test_three_distinct_keys_accessible_in_sequence(self, km):
        keys = []
        for _ in range(3):
            k = km.get_key()
            assert k is not None
            keys.append(k)
            km.release_key(k, KeyStatus.AVAILABLE)
        key_strings = {k.key_string for k in keys}
        assert len(key_strings) == 3


class TestEdgeCases:

    def test_empty_key_list_raises(self):
        with pytest.raises((ValueError, Exception)):
            KeyManager([], service_name="TEST")

    def test_service_name_gemini_sets_rpm_limit(self):
        km = KeyManager(["k"], service_name="GEMINI")
        assert km.rpm_limit > 0

    def test_service_name_groq_sets_rpm_limit(self):
        km = KeyManager(["k"], service_name="GROQ")
        assert km.rpm_limit > 0

    def test_release_key_with_exhausted_status(self, km):
        key = km.get_key()
        try:
            km.release_key(key, KeyStatus.EXHAUSTED)
        except Exception as e:
            pytest.fail(f"release_key EXHAUSTED raised: {e}")
