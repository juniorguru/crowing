import json
import subprocess
from unittest.mock import Mock

import pytest

from jg.crowing import llm
from jg.crowing.errors import LLMError
from jg.crowing.models import Post


def response(tags):
    return json.dumps(
        {
            "subtype": "success",
            "is_error": False,
            "result": "",
            "structured_output": {"tags": tags},
        }
    )


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(llm.shutil, "which", lambda name: "/bin/claude")
    run = Mock(
        return_value=subprocess.CompletedProcess([], 0, response(["python", "git"]), "")
    )
    monkeypatch.setattr(llm.subprocess, "run", run)
    return run


def test_generates_tags_from_title_and_text(provider):
    post = Post("Příručka: Git", "First paragraph.\n\nSecond paragraph.")
    tagged = llm.generate_tags(post)
    assert tagged == Post(post.title, post.text, ["python", "git"])
    assert post.tags == []
    call = provider.call_args
    payload = call.kwargs["input"].removeprefix(llm.TAG_PROMPT)
    assert json.loads(payload) == {"title": post.title, "text": post.text}
    assert call.kwargs["timeout"] == 120
    assert call.args[0][0] == "/bin/claude"
    assert call.args[0][call.args[0].index("--tools") + 1] == ""


def test_missing_provider_lists_supported_command_and_search_path(monkeypatch):
    monkeypatch.setattr(llm.shutil, "which", lambda name: None)
    monkeypatch.setenv("PATH", "/not-installed")
    with pytest.raises(
        LLMError, match="Supported providers: Claude.*claude on PATH=.*not-installed"
    ):
        llm.find_provider()


@pytest.mark.parametrize(
    "failure",
    [
        OSError("not executable"),
        subprocess.CalledProcessError(1, "claude"),
        subprocess.TimeoutExpired("claude", 10),
    ],
)
def test_uncallable_provider_reports_checked_path(provider, failure):
    provider.side_effect = failure
    with pytest.raises(LLMError, match="Unsuccessful check: /bin/claude --version"):
        llm.find_provider()


@pytest.mark.parametrize(
    "failure, message",
    [
        (OSError("gone"), "Could not run"),
        (subprocess.TimeoutExpired("claude", 120), "timed out"),
    ],
)
def test_generation_process_errors(provider, failure, message):
    provider.side_effect = [subprocess.CompletedProcess([], 0), failure]
    with pytest.raises(LLMError, match=message):
        llm.generate_tags(Post("Title", "Text"))


def test_generation_nonzero_exit_reports_provider_error(provider):
    provider.side_effect = [
        subprocess.CompletedProcess([], 0),
        subprocess.CompletedProcess([], 1, "", "Please sign in"),
    ]
    with pytest.raises(LLMError, match="Please sign in"):
        llm.generate_tags(Post("Title", "Text"))


@pytest.mark.parametrize(
    "output", ["not JSON", "{}", "null", "[]", "[1]", '[""]', '["#"]', '["two words"]']
)
def test_invalid_tags_fail(provider, output):
    provider.return_value.stdout = output
    with pytest.raises(LLMError):
        llm.generate_tags(Post("Title", "Text"))


def test_strips_hashes_and_deduplicates_tags(provider):
    provider.return_value.stdout = response([" #python ", "python", "čeština"])
    assert llm.generate_tags(Post("Title", "Text")).tags == ["python", "čeština"]


def test_requests_schema_constrained_output(provider):
    llm.generate_tags(Post("Title", "Text"))
    args = provider.call_args.args[0]
    assert args[args.index("--output-format") + 1] == "json"
    assert json.loads(args[args.index("--json-schema") + 1]) == llm.TAG_SCHEMA


@pytest.mark.parametrize("tags", [None, {}, [], [1], [""], ["#"], ["two words"]])
def test_invalid_structured_tags_fail(provider, tags):
    provider.return_value.stdout = response(tags)
    with pytest.raises(LLMError, match="nonempty JSON array"):
        llm.generate_tags(Post("Title", "Text"))


def test_ignores_freeform_result_when_structured_output_present(provider):
    envelope = json.loads(response(["python"]))
    envelope["result"] = 'Here are your tags: ```json\n["wrong"]\n```'
    provider.return_value.stdout = json.dumps(envelope)
    assert llm.generate_tags(Post("Title", "Text")).tags == ["python"]


def test_missing_structured_output_reports_clear_error(provider):
    provider.return_value.stdout = json.dumps(
        {"subtype": "success", "result": "Some prose"}
    )
    with pytest.raises(LLMError, match="no structured post tags"):
        llm.generate_tags(Post("Title", "Text"))


def test_provider_error_in_successful_process_is_reported(provider):
    provider.return_value.stdout = json.dumps(
        {
            "is_error": True,
            "subtype": "error_max_structured_output_retries",
            "errors": ["Could not satisfy schema"],
        }
    )
    with pytest.raises(LLMError, match="Could not satisfy schema"):
        llm.generate_tags(Post("Title", "Text"))
