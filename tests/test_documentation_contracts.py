from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = [
    ROOT / "README.md",
    *sorted((ROOT / "docs").rglob("*.md")),
    *sorted((ROOT / "wiki").rglob("*.md")),
]


def heading_slugs(path: Path) -> set[str]:
    headings = re.findall(r"^#+\s+(.+)$", path.read_text(), re.MULTILINE)
    return {
        re.sub(r"[- ]+", "-", re.sub(r"[^a-z0-9 -]", "", heading.lower())).strip("-")
        for heading in headings
    }


class DocumentationContractTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self) -> None:
        missing: list[str] = []
        for document in MARKDOWN_FILES:
            for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", document.read_text()):
                if target.startswith(("http://", "https://")):
                    continue
                relative, _, fragment = target.partition("#")
                path = document if not relative else document.parent / relative
                if not path.exists() and document.parent.name == "wiki":
                    path = path.with_suffix(".md")
                if not path.exists():
                    missing.append(f"{document.relative_to(ROOT)} -> {target}")
                elif fragment and fragment not in heading_slugs(path):
                    missing.append(f"{document.relative_to(ROOT)} -> #{fragment}")
        self.assertEqual(missing, [])

    def test_documented_just_targets_exist(self) -> None:
        justfile = (ROOT / "justfile").read_text()
        recipes = set(re.findall(r"^@?([a-z][a-z0-9_]*)[^:]*:", justfile, re.MULTILINE))
        documented = set()
        for document in [ROOT / "README.md", *(ROOT / "wiki").glob("*.md")]:
            documented.update(re.findall(r"\bjust ([a-z][a-z0-9_]*)", document.read_text()))
        self.assertEqual(documented - recipes, set())

    def test_wiki_has_every_linked_guide(self) -> None:
        expected = {
            "Home.md", "Setup.md", "Local-Workflow.md", "HPC-SLURM-Workflow.md",
            "Data-and-Splits.md", "Configuration-Reference.md",
            "Results-and-Interpretation.md", "Troubleshooting.md", "Contributing.md",
            "_Sidebar.md", "README.md",
        }
        self.assertEqual({path.name for path in (ROOT / "wiki").glob("*.md")}, expected)


if __name__ == "__main__":
    unittest.main()
