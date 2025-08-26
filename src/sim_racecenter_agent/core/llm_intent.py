"""Deprecated: heuristic / intent classification layer removed.

This module is retained as a stub to avoid import errors in any out-of-tree
code. All callers should migrate to the unified planning flow implemented in
`director.agent.DirectorAgent.answer` which performs LLM planning and answer
composition directly. Importing classify_intent_llm will raise to surface the
deprecation early during runtime if legacy code paths persist.
"""


def classify_intent_llm(*_args, **_kwargs):  # type: ignore
    raise RuntimeError(
        "llm_intent deprecated: single-mode agent now always uses planning+answer pipeline."
    )
