"""Honesty gates over packaging metadata and forked-scaffold lineage.

Three properties are enforced here, each of which was previously asserted in
prose (or by a shell one-liner that could not report what it claimed) and is
now enforced by a test that can go red:

1. **Declared runtime dependencies are exactly the third-party modules
   ``src/`` imports.** Manuscript §5.3 states the pure core runs on "the
   standard library plus ``pyyaml``". Before this gate, ``pyproject.toml`` also
   declared ``numpy``, ``matplotlib`` and ``defusedxml``, none of which is
   imported anywhere in the package.
2. **The ``bond-api`` path source is relative.** It was pinned to one machine's
   absolute home directory, which breaks every other checkout.
3. **No forked-scaffold lineage in identity surfaces.** The exemplar slug this
   package was scaffolded from must not appear in any source file, nor in any
   *value* of any structured identity/config file.

Scope of gate 3, stated plainly so it is not mistaken for more than it is: it
scans (a) every ``.py`` file under ``src/``, ``scripts/`` and ``tests/`` for the
literal slug, and (b) every scalar *value* reachable in the structured identity
files listed in :data:`STRUCTURED_IDENTITY_FILES`. It deliberately does **not**
scan Markdown prose or YAML/TOML comments, because this package's own
remediation notes discuss the fork by name on purpose. It therefore cannot
detect un-forked *narrative* text; that class of defect is not gated here and
must be caught by review.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only on Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Distribution name -> the top-level module name it installs.
DISTRIBUTION_TO_MODULE = {
    "pyyaml": "yaml",
    "bond-api": "bond_api",
}

#: Structured files whose *values* must not name the scaffold source.
STRUCTURED_IDENTITY_FILES = (
    "pyproject.toml",
    "manuscript/config.yaml",
    "CITATION.cff",
    "codemeta.json",
    ".zenodo.json",
    "domain_profile.yaml",
    "experiment_plan.yaml",
    "export.toml",
)

#: Assembled from fragments so this file does not match its own gate.
LINEAGE_MARKER = "template" + "_code_" + "project"


def _pyproject() -> dict[str, Any]:
    return tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text())


def _declared_runtime_distributions() -> set[str]:
    """Distribution names from ``[project].dependencies``, version specs stripped."""
    raw = _pyproject()["project"]["dependencies"]
    names: set[str] = set()
    for spec in raw:
        name = spec.split(";")[0]
        for separator in ("[", "<", ">", "=", "!", "~", " "):
            name = name.split(separator)[0]
        names.add(name.strip().lower())
    return names


def _imported_top_level_modules(*roots: Path) -> set[str]:
    """Top-level module names imported by every ``.py`` file under ``roots``.

    Uses the AST rather than a regex, so commented-out or string-literal
    "imports" cannot inflate the set and a lazy function-body import (as in
    ``film_providers.py``) is still counted.
    """
    modules: set[str] = set()
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules.add(node.module.split(".")[0])
    return modules


def _third_party(modules: set[str]) -> set[str]:
    """Drop standard-library and first-party modules from ``modules``."""
    first_party = {"bond_orchestrator", "tests", "conftest"}
    return {module for module in modules if module not in first_party and module not in sys.stdlib_module_names}


def _scalar_values(node: Any) -> list[str]:
    """Flatten a parsed structured document into its scalar values as strings."""
    if isinstance(node, dict):
        return [text for key, value in node.items() for text in ([str(key)] + _scalar_values(value))]
    if isinstance(node, (list, tuple)):
        return [text for item in node for text in _scalar_values(item)]
    return [] if node is None else [str(node)]


def _load_structured(path: Path) -> Any:
    if path.suffix == ".json" or path.name == ".zenodo.json":
        return json.loads(path.read_text())
    if path.suffix == ".toml":
        return tomllib.loads(path.read_text())
    return yaml.safe_load(path.read_text())


class TestDeclaredDependenciesMatchImports:
    """§5.3: the declared runtime dependency set is the imported set."""

    def test_declared_runtime_dependencies_are_imported(self) -> None:
        declared = _declared_runtime_distributions()
        assert declared, "no runtime dependencies declared; this gate would be vacuous"

        imported = _third_party(_imported_top_level_modules(PROJECT_ROOT / "src"))
        unused = {name for name in declared if DISTRIBUTION_TO_MODULE.get(name, name.replace("-", "_")) not in imported}
        assert not unused, (
            f"declared in pyproject.toml but imported nowhere under src/: {sorted(unused)}. "
            "Manuscript §5.3 states the pure core needs only the standard library plus pyyaml."
        )

    def test_every_third_party_import_is_declared(self) -> None:
        declared_modules = {
            DISTRIBUTION_TO_MODULE.get(name, name.replace("-", "_")) for name in _declared_runtime_distributions()
        }
        imported = _third_party(_imported_top_level_modules(PROJECT_ROOT / "src", PROJECT_ROOT / "scripts"))
        assert imported, "no third-party imports found; this gate would be vacuous"
        undeclared = imported - declared_modules
        assert not undeclared, f"imported under src/ or scripts/ but undeclared in pyproject.toml: {sorted(undeclared)}"

    def test_manuscript_dependency_sentence_matches_pyproject(self) -> None:
        """§5.3's named dependency is the one pyproject actually declares."""
        declared = _declared_runtime_distributions()
        assert declared == {"pyyaml", "bond-api"}, (
            f"runtime dependencies changed to {sorted(declared)}; "
            "update manuscript/05_experimental_setup.md §5.3 in the same commit."
        )


class TestPathDependencyIsPortable:
    """The bond-api path source must not pin a machine-specific location."""

    def test_bond_api_source_is_relative(self) -> None:
        source = _pyproject()["tool"]["uv"]["sources"]["bond-api"]
        path = Path(source["path"])
        assert not path.is_absolute(), (
            f"[tool.uv.sources].bond-api.path is absolute ({path}); "
            "an absolute path pins this package to one machine's filesystem."
        )

    def test_bond_api_source_resolves_to_a_real_package(self) -> None:
        source = _pyproject()["tool"]["uv"]["sources"]["bond-api"]
        resolved = (PROJECT_ROOT / source["path"]).resolve()
        assert (resolved / "pyproject.toml").is_file(), f"bond-api path does not resolve to a package: {resolved}"


class TestNoForkedScaffoldLineage:
    """No identity surface names the exemplar this package was scaffolded from."""

    @pytest.mark.parametrize("relative", STRUCTURED_IDENTITY_FILES)
    def test_structured_identity_values_are_clean(self, relative: str) -> None:
        path = PROJECT_ROOT / relative
        assert path.is_file(), f"{relative} is missing; the gate would silently skip it"
        values = _scalar_values(_load_structured(path))
        assert values, f"{relative} parsed to no values; the gate would be vacuous"
        offenders = [value for value in values if LINEAGE_MARKER in value]
        assert not offenders, f"{relative} carries forked-scaffold lineage in a declared value: {offenders}"

    def test_source_trees_are_clean(self) -> None:
        roots = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests")
        scanned = [path for root in roots for path in sorted(root.rglob("*.py"))]
        assert len(scanned) > 10, f"only {len(scanned)} files scanned; the gate would be near-vacuous"
        offenders = [str(path.relative_to(PROJECT_ROOT)) for path in scanned if LINEAGE_MARKER in path.read_text()]
        assert not offenders, f"forked-scaffold lineage in source: {offenders}"

    def test_the_marker_itself_is_detectable(self) -> None:
        """Positive control: the scan finds the marker when it is present.

        Without this, a green lineage gate could mean "the tree is clean" or
        "the needle is misspelled and matches nothing".
        """
        assert LINEAGE_MARKER == "template_code_" + "project"
        assert _scalar_values({"source_project": f"templates/{LINEAGE_MARKER}"}) == [
            "source_project",
            f"templates/{LINEAGE_MARKER}",
        ]
        planted = {"a": ["x", f"templates/{LINEAGE_MARKER}"], "b": {"c": 1}}
        assert [value for value in _scalar_values(planted) if LINEAGE_MARKER in value]
