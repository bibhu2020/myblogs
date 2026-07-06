"""Langfuse tracing, wired so it can never break an agent run.

If LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are unset, or anything about
Langfuse (import, client construction, network) fails, every function here
degrades to a no-op. Agents must call init_observability() once at startup
and flush_observability() in a finally block before the process exits —
Langfuse batches spans on a background thread, and these agents are
short-lived CLI processes that exit right after main() returns.
"""
import contextlib
import os
import sys

_ENABLED = False
_client = None


def init_observability(agent_name: str) -> None:
    global _ENABLED, _client

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not public_key or not secret_key:
        return

    try:
        from langfuse import get_client
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

        os.environ.setdefault("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

        client = get_client()
        OpenAIInstrumentor().instrument()
        OpenAIAgentsInstrumentor().instrument()

        _client = client
        _ENABLED = True
    except Exception as exc:
        print(f"[observability] Warning: Langfuse init failed for {agent_name} ({exc!r}) — continuing without tracing")
        _ENABLED = False
        _client = None


@contextlib.contextmanager
def traced_run(agent_name: str):
    """Enter the Langfuse span manually so a body exception can never be
    mistaken for a failed-to-start span (which would yield a second time —
    invalid for a generator-based context manager)."""
    span_cm = None
    span = None
    if _ENABLED and _client is not None:
        try:
            span_cm = _client.start_as_current_span(name=f"{agent_name}_run")
            span = span_cm.__enter__()
        except Exception as exc:
            print(f"[observability] Warning: could not start trace span ({exc!r}) — continuing without tracing")
            span_cm = None

    if span_cm is None:
        yield None
        return

    try:
        yield span
    except BaseException:
        span_cm.__exit__(*sys.exc_info())
        raise
    else:
        span_cm.__exit__(None, None, None)


def get_langchain_handler():
    if not _ENABLED:
        return None
    try:
        from langfuse.langchain import CallbackHandler
        return CallbackHandler()
    except Exception as exc:
        print(f"[observability] Warning: could not create LangChain handler ({exc!r})")
        return None


def observe(name: str | None = None):
    if not _ENABLED:
        return lambda fn: fn
    try:
        from langfuse import observe as _langfuse_observe
        return _langfuse_observe(name=name)
    except Exception as exc:
        print(f"[observability] Warning: @observe unavailable ({exc!r}) — running undecorated")
        return lambda fn: fn


def flush_observability() -> None:
    if not _ENABLED or _client is None:
        return
    try:
        _client.flush()
    except Exception as exc:
        print(f"[observability] Warning: flush failed ({exc!r})")
