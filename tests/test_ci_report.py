"""tools/ci_report.py is how a cloud session learns how many tests ran in CI and
which failed, because it cannot read raw CI logs. If it miscounts, every later
"CI is green" is a guess. Standard library only.
"""

import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import ci_report  # noqa: E402

JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="5">
  <testcase classname="tests.test_a" name="test_ok"/>
  <testcase classname="tests.test_a" name="test_ok_too"/>
  <testcase classname="tests.test_a" name="test_bad"><failure message="assert 1 == 2&#10;more">tb</failure></testcase>
  <testcase classname="tests.test_b" name="test_boom"><error message="ImportError: x">tb</error></testcase>
  <testcase classname="tests.test_b" name="test_later"><skipped message="needs ezdxf"/></testcase>
</testsuite></testsuites>
"""


def _junit():
    fd, path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(JUNIT)
    return path


def test_counts_are_exact():
    line, problems = ci_report.summarise(_junit())
    assert line == "2 passed, 1 failed, 1 errors, 1 skipped (5)", line
    assert [n for n, _ in problems] == ["tests.test_a::test_bad", "tests.test_b::test_boom"]


def test_annotations_are_well_formed_and_escaped():
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ci_report.py"),
                           _junit(), "pytest ubuntu-latest py3.13"],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert proc.returncode == 0
    lines = proc.stdout.splitlines()
    assert lines[0] == ("::notice title=pytest ubuntu-latest py3.13::"
                        "2 passed, 1 failed, 1 errors, 1 skipped (5)")
    errors = [l for l in lines if l.startswith("::error ")]
    assert len(errors) == 2
    # Only the first line of a multi-line message, and no raw newline inside.
    assert "assert 1 == 2" in errors[0] and "more" not in errors[0]


def test_a_missing_report_is_an_error_not_silence():
    proc = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "ci_report.py"),
                           os.path.join(tempfile.gettempdir(), "nope-junit.xml"), "pytest x"],
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)
    assert proc.stdout.startswith("::error title=pytest x::no JUnit report")
