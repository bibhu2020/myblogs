import pytest

from meridian_agents import observability


@pytest.fixture(autouse=True)
def _reset_observability_state(monkeypatch):
    """Every test starts from a clean slate — module-level globals must not leak
    between tests since init_observability() mutates them as a side effect."""
    monkeypatch.setattr(observability, "_ENABLED", False)
    monkeypatch.setattr(observability, "_client", None)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    yield


def test_init_without_keys_stays_disabled():
    observability.init_observability("test_agent")
    assert observability._ENABLED is False


def test_init_without_keys_leaves_helpers_as_no_ops():
    observability.init_observability("test_agent")

    assert observability.get_langchain_handler() is None

    calls = []

    @observability.observe(name="thing")
    def fn(x):
        calls.append(x)
        return x * 2

    assert fn(3) == 6
    assert calls == [3]

    observability.flush_observability()  # must not raise


def test_init_with_keys_but_missing_dependency_falls_back_to_disabled(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    # langfuse (or its transitive instrumentors) isn't guaranteed to be
    # installed in every environment — simulate that failure path explicitly.
    import builtins
    real_import = builtins.__import__

    def _failing_import(name, *args, **kwargs):
        if name == "langfuse" or name.startswith("openinference"):
            raise ImportError(f"simulated missing dependency: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _failing_import)

    observability.init_observability("test_agent")  # must not raise

    assert observability._ENABLED is False
    assert observability.get_langchain_handler() is None


def test_traced_run_yields_and_does_not_raise_when_disabled():
    observability.init_observability("test_agent")
    with observability.traced_run("test_agent") as span:
        assert span is None


def test_traced_run_propagates_exceptions_from_the_body():
    observability.init_observability("test_agent")
    with pytest.raises(ValueError, match="boom"):
        with observability.traced_run("test_agent"):
            raise ValueError("boom")


def test_traced_run_propagates_exceptions_when_enabled(monkeypatch):
    """Even with a live span, a body exception must come out of the `with`
    block unchanged rather than being swallowed or replaced by a second
    (invalid) generator yield."""
    monkeypatch.setattr(observability, "_ENABLED", True)

    class _FakeSpan:
        def __enter__(self):
            return "fake-span"

        def __exit__(self, exc_type, exc, tb):
            return False  # do not suppress

    class _FakeClient:
        def start_as_current_span(self, name):
            return _FakeSpan()

    monkeypatch.setattr(observability, "_client", _FakeClient())

    with pytest.raises(ValueError, match="boom"):
        with observability.traced_run("test_agent") as span:
            assert span == "fake-span"
            raise ValueError("boom")


def test_traced_run_falls_back_when_span_start_fails(monkeypatch):
    monkeypatch.setattr(observability, "_ENABLED", True)

    class _FakeClient:
        def start_as_current_span(self, name):
            raise RuntimeError("langfuse unreachable")

    monkeypatch.setattr(observability, "_client", _FakeClient())

    with observability.traced_run("test_agent") as span:
        assert span is None  # degraded to no-op instead of raising
