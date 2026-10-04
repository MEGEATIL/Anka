# -*- coding: utf-8 -*-
"""ANKA AI Geliştirici & Kodlama Modu Motoru."""

import os
import subprocess
from typing import Any, Dict, List, Optional


class DeveloperCodingMode:
    """Yazılım projelerini tarayan, bağımlılıkları analiz eden, testleri çalıştıran,
    hataları tespit eden ve onaylı kod değişiklikleri hazırlayan geliştirici motoru."""

    def __init__(self, project_root: str = "."):
        self.project_root = os.path.abspath(project_root)

    def scan_project(self) -> Dict[str, Any]:
        """Proje yapısını ve temel bağımlılık dosyalarını tarar."""
        files = []
        deps = []

        for root, dirs, filenames in os.walk(self.project_root):
            # Gizli ve sanal ortam dizinlerini atla
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "build", "dist", "__pycache__")]
            for f in filenames:
                rel_path = os.path.relpath(os.path.join(root, f), self.project_root)
                files.append(rel_path)
                if f in ("requirements.txt", "package.json", "pyproject.toml", "Cargo.toml"):
                    deps.append(rel_path)

        return {
            "project_root": self.project_root,
            "total_files": len(files),
            "dependency_files": deps,
            "sample_files": files[:15],
        }

    def run_tests(self, test_command: str = "pytest") -> Dict[str, Any]:
        """Projedeki otomatik testleri çalıştırır ve çıktıları raporlar."""
        try:
            res = subprocess.run(
                test_command,
                shell=True,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return {
                "success": res.returncode == 0,
                "return_code": res.returncode,
                "stdout": res.stdout[:2000],
                "stderr": res.stderr[:2000],
            }
        except Exception as exc:
            return {"success": False, "error": f"Test çalıştırılamadı: {exc}"}

    def propose_code_change(self, target_file: str, new_content: str) -> Dict[str, Any]:
        """Kod değişikliği teklifi hazırlar (kullanıcı onayı gerektirir)."""
        abs_path = os.path.join(self.project_root, target_file)
        file_exists = os.path.exists(abs_path)

        return {
            "target_file": target_file,
            "abs_path": abs_path,
            "exists": file_exists,
            "new_content_preview": new_content[:500],
            "requires_user_approval": True,
        }

    def apply_code_change(self, proposal: Dict[str, Any]) -> bool:
        """Kullanıcı tarafından onaylanan kod değişikliğini uygular."""
        if not proposal.get("requires_user_approval", True):
            return False

        abs_path = proposal.get("abs_path")
        content = proposal.get("new_content", proposal.get("new_content_preview", ""))

        if not abs_path:
            return False

        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False
