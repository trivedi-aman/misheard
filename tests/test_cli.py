import io
import subprocess
import sys

import pytest

from misheard.cli import main


@pytest.fixture
def places(tmp_path):
    path = tmp_path / "places.txt"
    path.write_text("# districts\nBarmer\nJaipur\n\nBLR\tBengaluru\nBLR\tBangalore\nMangalore\n", encoding="utf-8")
    return str(path)


def run(capsys, *argv):
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_compare_two_names(capsys):
    code, out, _ = run(capsys, "Barmer", "बाड़मेर")
    assert code == 0
    assert out.startswith("Barmer ↔ बाड़मेर (baaṛmer)   distance 0.4")
    assert "retroflex flap" in out


def test_quiet_prints_only_the_distance(capsys):
    assert run(capsys, "-q", "Mohan", "Rohan") == (0, "1.7\n", "")


def test_refs(capsys, places):
    code, out, _ = run(capsys, "--refs", places, "Baadmer", "Bangalor", "-n", "2")
    assert code == 0
    blocks = out.split("\n\n")
    assert blocks[0].splitlines()[:2] == ["Baadmer", "    0.60  Barmer"]
    assert blocks[1].splitlines()[1] == "    0.60  Bangalore  [BLR]"
    assert all(len(b.splitlines()) == 3 for b in blocks)
    assert not any(line != line.rstrip() for line in out.splitlines())


def test_refs_heard_from_stdin(capsys, places, monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("Baadmer\n\nJaypur\n"))
    assert run(capsys, "-r", places, "-q") == (0, "0.6\tBarmer\n0\tJaipur\n", "")


def test_confusions_file(capsys, tmp_path):
    csv = tmp_path / "c.csv"
    csv.write_text("a,b,cost,why\nm,r,0.1,test row\n", encoding="utf-8")
    code, out, _ = run(capsys, "-c", str(csv), "Mohan", "Rohan")
    assert code == 0 and "distance 0.1" in out and "test row" in out
    assert run(capsys, "-q", "--no-default-confusions", "Vinod", "Binod")[1] != \
           run(capsys, "-q", "Vinod", "Binod")[1]


@pytest.mark.parametrize("argv, message", [
    (["Ganesh", "గణేష్"], "Telugu"),
    (["--refs", "/nonexistent/places.txt", "Barmer"], "No such file"),
])
def test_errors_go_to_stderr_with_exit_code_1(capsys, argv, message):
    code, out, err = run(capsys, *argv)
    assert code == 1 and out == "" and message in err


@pytest.mark.parametrize("argv", [["Mohan"], ["a", "b", "c"], ["--refs", "x", "-n", "0", "a"]])
def test_usage_errors_exit_2(capsys, argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_python_dash_m():
    out = subprocess.run([sys.executable, "-m", "misheard", "-q", "Barmer", "Baadmer"],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    assert out == "0.6\n"
