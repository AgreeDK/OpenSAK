# tests/unit-tests/test_derive_msix_version_script.py — scripts/derive_msix_version.py
#
# Coverage for the OpenSAK-version -> 4-part-numeric-MSIX-version mapping
# used by the MSIX CI packaging job (#786 step 3). Never touches the real
# repo's __init__.py.

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "derive_msix_version.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("derive_msix_version", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def dv(tmp_path, monkeypatch):
    """A freshly loaded copy of the script, pointed at a throwaway
    __init__.py instead of the real repo's."""
    module = _load_module()
    init_py = tmp_path / "__init__.py"
    init_py.write_text(
        '__version__ = "1.18.0-beta.1"\n__author__ = "OpenSAK Contributors"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "INIT_PY", init_py)
    return module


class TestDeriveMsixVersion:
    def test_stable_release_gets_zero_revision(self, dv):
        assert dv.derive_msix_version("1.18.0") == "1.18.0.0"

    def test_beta_suffix_becomes_revision(self, dv):
        assert dv.derive_msix_version("1.18.0-beta.1") == "1.18.0.1"

    def test_multi_digit_beta_number(self, dv):
        assert dv.derive_msix_version("1.17.2-beta.12") == "1.17.2.12"

    def test_other_suffix_words_work_the_same_way(self, dv):
        assert dv.derive_msix_version("2.0.0-rc.1") == "2.0.0.1"

    def test_rejects_malformed_version(self, dv):
        with pytest.raises(ValueError):
            dv.derive_msix_version("not-a-version")

    def test_rejects_version_missing_patch_number(self, dv):
        with pytest.raises(ValueError):
            dv.derive_msix_version("1.18")


class TestGetInitVersion:
    def test_reads_version_from_init_py(self, dv):
        assert dv.get_init_version() == "1.18.0-beta.1"


class TestMainCLI:
    def test_prints_derived_version_from_init_py(self, dv, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["derive_msix_version.py"])
        dv.main()
        assert capsys.readouterr().out.strip() == "1.18.0.1"

    def test_accepts_explicit_version_argument(self, dv, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["derive_msix_version.py", "1.19.0-beta.4"])
        dv.main()
        assert capsys.readouterr().out.strip() == "1.19.0.4"

    def test_strips_leading_v(self, dv, monkeypatch, capsys):
        monkeypatch.setattr(sys, "argv", ["derive_msix_version.py", "v1.19.0-beta.4"])
        dv.main()
        assert capsys.readouterr().out.strip() == "1.19.0.4"

    def test_rejects_malformed_argument_and_exits_nonzero(self, dv, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["derive_msix_version.py", "not-a-version"])
        with pytest.raises(SystemExit) as exc:
            dv.main()
        assert exc.value.code == 1

    def test_too_many_arguments_exits_nonzero(self, dv, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["derive_msix_version.py", "1.0.0", "extra"])
        with pytest.raises(SystemExit) as exc:
            dv.main()
        assert exc.value.code == 1
