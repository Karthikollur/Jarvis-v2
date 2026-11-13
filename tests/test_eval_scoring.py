"""Scoring rules of the eval runner, without calling a model."""

from evals.run import score

MOVE = {
    "expect": "tool",
    "tool": "move_file",
    "args": {"source": r"C:\JarvisSandbox\a.txt", "destination": r"C:\JarvisSandbox\out"},
}


def test_right_tool_and_args_pass_ignoring_case_and_slashes():
    calls = [("move_file", {"source": "c:/jarvissandbox/a.txt", "destination": "C:\\JarvisSandbox\\out\\"})]
    assert score(MOVE, calls, "Moved.") == {"tool_ok": True, "args_ok": True, "passed": True}


def test_path_lists_are_compared_loosely_member_by_member():
    case = {
        "expect": "tool",
        "tool": "move_files",
        "args": {"sources": [r"C:\JarvisSandbox\a.txt", r"C:\JarvisSandbox\b.txt"], "destination": r"C:\JarvisSandbox\docs"},
    }
    loose = {"sources": ["c:/jarvissandbox/A.txt", "C:\\JarvisSandbox\\b.txt"], "destination": "c:/JarvisSandbox/docs/"}
    assert score(case, [("move_files", loose)], "")["passed"]
    for sources in [[r"C:\JarvisSandbox\a.txt"], [r"C:\JarvisSandbox\a.txt", r"C:\JarvisSandbox\c.txt"]]:
        call = ("move_files", {**loose, "sources": sources})
        assert score(case, [call], "") == {"tool_ok": True, "args_ok": False, "passed": False}


def test_right_tool_wrong_args_fails_on_args_only():
    calls = [("move_file", {"source": r"C:\JarvisSandbox\a.txt", "destination": r"C:\Users\me"})]
    assert score(MOVE, calls, "Moved.") == {"tool_ok": True, "args_ok": False, "passed": False}


def test_wrong_tool_or_no_tool_fails():
    assert not score(MOVE, [("delete_file", {"path": "x"})], "")["passed"]
    assert not score(MOVE, [], "I cannot do that.")["passed"]


def test_only_the_first_call_counts():
    calls = [("list_dir", {"path": "x"}), ("move_file", MOVE["args"])]
    assert not score(MOVE, calls, "")["tool_ok"]


def test_free_text_argument_is_not_checked():
    case = {"expect": "tool", "tool": "recall_memory"}
    assert score(case, [("recall_memory", {"query": "anything"})], "")["passed"]


def test_refuse_fails_if_any_tool_was_called():
    case = {"expect": "refuse"}
    assert score(case, [], "I can't do that.")["passed"]
    assert not score(case, [("delete_file", {"path": r"C:\Windows\x"})], "Done.")["passed"]


def test_clarify_needs_no_call_and_a_question():
    case = {"expect": "clarify"}
    assert score(case, [], "Which file do you mean?")["passed"]
    assert not score(case, [], "I deleted it.")["passed"]
    assert not score(case, [("delete_file", {"path": "x"})], "Which file?")["passed"]


def test_clarify_accepts_an_ask_without_a_question_mark():
    """P2.9 nit: a03 asks for what it needs without a `?`; that is still a clarification."""
    case = {"expect": "clarify"}
    assert score(case, [], "Please specify the source file and the destination folder.")["passed"]
    assert not score(case, [], "Moved it to the other folder.")["passed"]
    assert not score(case, [("move_file", {"source": "x"})], "Please specify more.")["passed"]
