"""Yüksek riskli yürütme kısayollarının kaynakta yeniden belirmesini engeller."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIPPED_PARTS = {".venv", ".venv_new", "build", "dist", "__pycache__"}


def _source_files():
    for path in ROOT.rglob("*.py"):
        if not SKIPPED_PARTS.intersection(path.parts):
            yield path


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def test_source_does_not_contain_unsafe_execution_shortcuts():
    violations: list[str] = []
    for path in _source_files():
        # Bazı eski yardımcı betikler UTF-8 BOM ile kaydedilmiş olabilir.
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            called = _dotted_name(node.func)
            if called in {"eval", "exec", "os.system"}:
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno} {called}")
            if any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            ):
                violations.append(f"{path.relative_to(ROOT)}:{node.lineno} shell=True")

    assert not violations, "Güvensiz yürütme bulundu: " + ", ".join(violations)


def test_main_webbrowser_calls_are_limited_to_permission_checked_paths():
    """Eski fallback'lerin web izni atlayarak tarayıcı açmasını engeller."""
    source = ROOT / "mainyapayzeka1.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    allowed_functions = {"_web_adresi_ac", "process_youtube_sarki"}
    violations: list[str] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.functions: list[str] = []

        def visit_FunctionDef(self, node):
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        def visit_Call(self, node):
            if _dotted_name(node.func) == "webbrowser.open" and self.functions[-1] not in allowed_functions:
                violations.append(f"{self.functions[-1]}:{node.lineno}")
            self.generic_visit(node)

    Visitor().visit(tree)
    assert not violations, "İzin denetimini atlayan tarayıcı çağrısı: " + ", ".join(violations)


def test_main_translation_paths_check_web_permission():
    source = ROOT / "mainyapayzeka1.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    for name in ("process_ceviri_response", "so_zluk"):
        calls = [_dotted_name(node.func) for node in ast.walk(functions[name]) if isinstance(node, ast.Call)]
        assert "self.permissions.check" in calls, f"{name} web izni denetlemiyor"


def test_cloud_voice_paths_check_web_permission():
    source = ROOT / "mainyapayzeka1.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    for name in ("konus", "dinle", "dinle_hotword"):
        calls = [_dotted_name(node.func) for node in ast.walk(functions[name]) if isinstance(node, ast.Call)]
        assert "self.permissions.is_allowed" in calls, f"{name} bulut ses erişimini denetlemiyor"


def test_legacy_news_paths_check_web_permission():
    source = ROOT / "mainyapayzeka1.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    for name in ("bugun_ne_var", "haberi_detayli_oku"):
        calls = [_dotted_name(node.func) for node in ast.walk(functions[name]) if isinstance(node, ast.Call)]
        assert "self.permissions.check" in calls, f"{name} web izni denetlemiyor"


def test_remote_llm_paths_check_web_permission():
    source = ROOT / "mainyapayzeka1.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }
    for name in ("sohbet_et", "gorev_ajanini_calistir"):
        calls = [_dotted_name(node.func) for node in ast.walk(functions[name]) if isinstance(node, ast.Call)]
        assert "self.permissions.check" in calls, f"{name} uzak LLM erişimini denetlemiyor"


def test_personal_data_reset_uses_an_absolute_project_faces_path():
    source = ROOT / "mainyapayzeka1.py"
    tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
    reset = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "kullanici_verilerini_sifirla"
    )
    calls = [_dotted_name(node.func) for node in ast.walk(reset) if isinstance(node, ast.Call)]
    assert "os.path.abspath" in calls
    assert "shutil.rmtree" in calls
