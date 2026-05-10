#!/usr/bin/env python3
"""Travel Concierge — repo hygiene audit (report-only).

Run from anywhere:

    python scripts/repo_hygiene_audit.py

The audit prints a concise Markdown report and **never deletes files**.
It is intended to be run before cleanup PRs, after major phases, and
whenever the test suite or workflow surface grows. See
``docs/ai/REPO_HYGIENE.md`` for the policy this audit enforces.

Hard exit code:
    0  — no hard blockers
    1  — at least one hard blocker (banned legacy path reintroduced
         or oversized handoff/miss-ledger raw-dump). Cleanup-only
         signals stay at exit 0; only true regressions fail the gate.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

HANDOFF_LINE_LIMIT = 500
HANDOFF_HARD_BYTES = 200_000  # raw-dump territory
MISS_LEDGER_LINE_LIMIT = 800
MISS_LEDGER_HARD_BYTES = 250_000

# Banned legacy paths — reintroducing any of these is a hard regression.
BANNED_PATHS: Tuple[str, ...] = (
    ".claude-flow",
    ".kiro",
    "graphify-out",
    ".opencode.json",
    ".cursorrules",
    ".windsurfrules",
    "GEMINI.md",
    "docs/ai/progress_log.md",
    "progress_log.md",
    "docs/ai/PRODUCT_SURFACE_AUDIT.md",
    "docs/ai/MERGE_GATE_AUDIT_2026-05-01.md",
    "docs/ai/HANDOFF_2026-05-10_OS_V4_CONSOLIDATION.md",
    "docs/ai/skills",
)

# Banned source-content regressions — these phrases must not appear in
# production-visible code paths. Limited to obvious sample/fake markers.
BANNED_VISIBLE_TOKENS: Tuple[str, ...] = (
    "book.example.com",
)

# Production-visible scan roots (frontend UI + backend response paths only).
VISIBLE_SCAN_ROOTS: Tuple[str, ...] = (
    "frontend/src",
)

# Phrases that suggest a doc/handoff is acting as a raw dump.
RAW_DUMP_MARKERS: Tuple[str, ...] = (
    "BEGIN PR BODY",
    "END PR BODY",
    "----- BEGIN LOG -----",
    "Conversation transcript:",
    "===== TRANSCRIPT =====",
)

# Directories that look like test/cache/build noise if they accidentally
# get committed.
ACCIDENTAL_TRACKED_DIRS: Tuple[str, ...] = (
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    "node_modules",
    ".venv",
    "venv",
    "out",
)


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    label: str
    detail: str = ""

    def render(self) -> str:
        if self.detail:
            return f"- **{self.label}** — {self.detail}"
        return f"- **{self.label}**"


@dataclass
class Report:
    summary: List[str] = field(default_factory=list)
    hard_blockers: List[Finding] = field(default_factory=list)
    cleanup_candidates: List[Finding] = field(default_factory=list)
    test_findings: List[Finding] = field(default_factory=list)
    handoff_findings: List[Finding] = field(default_factory=list)
    docs_findings: List[Finding] = field(default_factory=list)
    next_pr_recommendation: List[str] = field(default_factory=list)

    def render(self) -> str:
        out: List[str] = []
        out.append("# Repo Hygiene Audit\n")
        out.append("## Summary\n")
        out.extend(self.summary or ["- (no summary lines)"])
        out.append("")

        out.append("## Hard blockers\n")
        if self.hard_blockers:
            out.extend(f.render() for f in self.hard_blockers)
        else:
            out.append("- none")
        out.append("")

        out.append("## Cleanup candidates\n")
        if self.cleanup_candidates:
            out.extend(f.render() for f in self.cleanup_candidates)
        else:
            out.append("- none")
        out.append("")

        out.append("## Test hygiene findings\n")
        if self.test_findings:
            out.extend(f.render() for f in self.test_findings)
        else:
            out.append("- none")
        out.append("")

        out.append("## Progress/handoff findings\n")
        if self.handoff_findings:
            out.extend(f.render() for f in self.handoff_findings)
        else:
            out.append("- none")
        out.append("")

        out.append("## Docs/artifact findings\n")
        if self.docs_findings:
            out.extend(f.render() for f in self.docs_findings)
        else:
            out.append("- none")
        out.append("")

        out.append("## Recommended next cleanup PR\n")
        if self.next_pr_recommendation:
            out.extend(f"- {line}" for line in self.next_pr_recommendation)
        else:
            out.append("- (nothing actionable beyond report-only signals)")
        out.append("")
        return "\n".join(out)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def git_ls_files() -> List[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def grep_for(pattern: str, paths: Sequence[Path]) -> List[Tuple[Path, int]]:
    """Return list of (path, line_number) where pattern is found.

    Pure-Python so we don't depend on rg/grep being installed.
    """
    hits: List[Tuple[Path, int]] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                hits.append((path, idx))
    return hits


def iter_files(roots: Iterable[str], suffixes: Tuple[str, ...]) -> Iterable[Path]:
    for root in roots:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in suffixes:
                continue
            yield path


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_banned_paths(tracked: List[str], report: Report) -> None:
    tracked_set = set(tracked)
    for banned in BANNED_PATHS:
        # exact tracked file
        if banned in tracked_set:
            report.hard_blockers.append(
                Finding(
                    "Banned legacy path reintroduced",
                    f"`{banned}` is tracked in git again",
                )
            )
            continue
        # tracked directory prefix (banned is dir)
        if any(t.startswith(banned + "/") for t in tracked_set):
            report.hard_blockers.append(
                Finding(
                    "Banned legacy directory reintroduced",
                    f"files under `{banned}/` are tracked again",
                )
            )


def check_visible_banned_tokens(report: Report) -> None:
    """Flag fake/sample tokens in production-visible source.

    This is a *review-only* signal because the same tokens legitimately
    appear in fail-closed guard code (e.g., a `MOCK_BOOKING_HOST` sentinel
    used to refuse fabricated data). We surface them so a reviewer can
    confirm context, but we do not hard-fail.
    """
    paths = list(iter_files(VISIBLE_SCAN_ROOTS, (".tsx", ".ts", ".js", ".jsx", ".mjs")))
    guard_markers = ("guard", "mock", "sentinel", "refuse", "fail-closed", "fail_closed")
    for token in BANNED_VISIBLE_TOKENS:
        hits = grep_for(token, paths)
        review_hits: List[Tuple[Path, int]] = []
        suspicious_hits: List[Tuple[Path, int]] = []
        for path, line in hits:
            try:
                text = path.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                text = ""
            if any(marker in text for marker in guard_markers):
                review_hits.append((path, line))
            else:
                suspicious_hits.append((path, line))
        if suspicious_hits:
            sample = ", ".join(
                f"{p.relative_to(REPO_ROOT)}:{ln}" for p, ln in suspicious_hits[:3]
            )
            extra = "" if len(suspicious_hits) <= 3 else f" (+{len(suspicious_hits) - 3} more)"
            report.hard_blockers.append(
                Finding(
                    f"Banned production-visible token `{token}` (no guard context)",
                    f"{sample}{extra}",
                )
            )
        if review_hits:
            sample = ", ".join(
                f"{p.relative_to(REPO_ROOT)}:{ln}" for p, ln in review_hits[:3]
            )
            extra = "" if len(review_hits) <= 3 else f" (+{len(review_hits) - 3} more)"
            report.docs_findings.append(
                Finding(
                    f"Token `{token}` appears in guard code (review only)",
                    f"{sample}{extra}",
                )
            )


def check_handoff_discipline(report: Report) -> None:
    targets = {
        "docs/ai/HANDOFF.md": (HANDOFF_LINE_LIMIT, HANDOFF_HARD_BYTES),
        "docs/ai/MISS_LEDGER.md": (MISS_LEDGER_LINE_LIMIT, MISS_LEDGER_HARD_BYTES),
    }
    for rel, (line_limit, byte_hard_limit) in targets.items():
        path = REPO_ROOT / rel
        if not path.exists():
            continue
        size = path.stat().st_size
        line_count = sum(1 for _ in path.open("r", encoding="utf-8", errors="replace"))
        if size > byte_hard_limit:
            report.hard_blockers.append(
                Finding(
                    "Progress/handoff oversized raw-dump",
                    f"`{rel}` is {size:,} bytes (>{byte_hard_limit:,}); compress before next PR",
                )
            )
        elif line_count > line_limit:
            report.handoff_findings.append(
                Finding(
                    "Progress/handoff over soft line limit",
                    f"`{rel}` has {line_count} lines (>{line_limit}); compress before next PR",
                )
            )
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in RAW_DUMP_MARKERS:
            if marker in text:
                report.handoff_findings.append(
                    Finding(
                        "Raw-dump marker in handoff",
                        f"`{rel}` contains `{marker}` — replace with summary + pointer",
                    )
                )


def check_test_hygiene(report: Report) -> None:
    backend_tests = REPO_ROOT / "backend" / "tests"
    frontend_tests = REPO_ROOT / "frontend" / "tests"
    pkg_json = REPO_ROOT / "frontend" / "package.json"

    # --- backend ---
    if backend_tests.exists():
        all_test_files = sorted(p for p in backend_tests.glob("test_*.py"))
        report.summary.append(f"- Backend test files: {len(all_test_files)}")
        # Try pytest collection if available
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q"],
                cwd=REPO_ROOT / "backend",
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            result = None

        if result is not None and result.returncode == 0:
            collected = set()
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or "::" not in line:
                    continue
                mod = line.split("::", 1)[0]
                if mod.startswith("tests/"):
                    collected.add(mod)
            collected_files = sorted(collected)
            report.summary.append(f"- Backend tests collected: {len(collected_files)} modules")
            on_disk = {f"tests/{p.name}" for p in all_test_files}
            uncollected = sorted(on_disk - set(collected_files))
            if uncollected:
                report.test_findings.append(
                    Finding(
                        "Backend test files not collected",
                        ", ".join(uncollected),
                    )
                )
        elif result is not None:
            report.test_findings.append(
                Finding(
                    "pytest --collect-only failed",
                    f"exit={result.returncode}; investigate before deleting tests",
                )
            )
        else:
            report.test_findings.append(
                Finding(
                    "pytest not available",
                    "skipped backend collection — install pytest to enable this check",
                )
            )

        # Detect imports of likely-deleted/legacy modules
        legacy_module_markers = (
            "from app.db.mock_search ",
            "from app.routes.legacy_search",
            "import app.routes.legacy_search",
            "from app.services.mock_provider",
        )
        suspicious: List[Path] = []
        for tf in all_test_files:
            try:
                text = tf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if any(m in text for m in legacy_module_markers):
                suspicious.append(tf)
        if suspicious:
            report.test_findings.append(
                Finding(
                    "Tests import legacy/removed modules",
                    ", ".join(p.name for p in suspicious),
                )
            )

        # Largest backend test files (signal for cleanup attention only)
        with_size = sorted(
            ((p, p.stat().st_size) for p in all_test_files),
            key=lambda t: t[1],
            reverse=True,
        )
        biggest = ", ".join(
            f"{p.name} ({sz // 1024}KB)" for p, sz in with_size[:3]
        )
        if biggest:
            report.summary.append(f"- Largest backend tests: {biggest}")

    # --- frontend ---
    if frontend_tests.exists():
        all_fe = sorted(frontend_tests.glob("*.test.mjs"))
        report.summary.append(f"- Frontend test files: {len(all_fe)}")
        configured: set = set()
        if pkg_json.exists():
            try:
                pkg_text = pkg_json.read_text(encoding="utf-8")
            except OSError:
                pkg_text = ""
            # Crude parse: look for `node --test tests/...`
            for match in re.finditer(r"tests/[\w\-./]+\.test\.mjs", pkg_text):
                configured.add(match.group(0))
            report.summary.append(
                f"- Frontend tests wired into package.json: {len(configured)}"
            )
            disk_rels = {f"tests/{p.name}" for p in all_fe}
            orphans = sorted(disk_rels - configured)
            if orphans:
                report.test_findings.append(
                    Finding(
                        "Frontend tests outside package.json scripts",
                        ", ".join(orphans),
                    )
                )


def check_accidental_tracked_dirs(tracked: List[str], report: Report) -> None:
    for marker in ACCIDENTAL_TRACKED_DIRS:
        hits = [t for t in tracked if f"/{marker}/" in t or t.startswith(marker + "/")]
        if hits:
            report.cleanup_candidates.append(
                Finding(
                    f"Generated/cache dir tracked: `{marker}/`",
                    f"{len(hits)} files; verify they should be in git, otherwise gitignore + git rm",
                )
            )


def check_orphan_artifact_pdfs(tracked: List[str], report: Report) -> None:
    pdfs = [t for t in tracked if t.lower().endswith(".pdf")]
    if not pdfs:
        return
    for pdf in pdfs:
        # search non-pdf files for references to the basename
        base = Path(pdf).name
        refs = subprocess.run(
            ["git", "grep", "-l", base],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        ref_files = [
            line for line in refs.stdout.splitlines()
            if line and line != pdf
        ]
        if not ref_files:
            report.docs_findings.append(
                Finding(
                    "Orphan PDF artifact",
                    f"`{pdf}` is not referenced anywhere in tracked text files",
                )
            )


def build_recommendations(report: Report) -> None:
    if report.hard_blockers:
        report.next_pr_recommendation.append(
            "Resolve hard blockers above before any other cleanup PR."
        )
    if report.handoff_findings:
        report.next_pr_recommendation.append(
            "Compress `docs/ai/HANDOFF.md` / `docs/ai/MISS_LEDGER.md` "
            "(replace, do not append) before next meaningful PR."
        )
    if report.test_findings:
        report.next_pr_recommendation.append(
            "Triage flagged tests: confirm they target active behavior or remove them in a focused test-cleanup PR."
        )
    if report.cleanup_candidates or report.docs_findings:
        report.next_pr_recommendation.append(
            "Bundle remaining cleanup candidates into a single small PR; preserve canonical artifacts."
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> int:
    report = Report()
    tracked = git_ls_files()
    report.summary.append(f"- Tracked files: {len(tracked)}")

    check_banned_paths(tracked, report)
    check_visible_banned_tokens(report)
    check_handoff_discipline(report)
    check_test_hygiene(report)
    check_accidental_tracked_dirs(tracked, report)
    check_orphan_artifact_pdfs(tracked, report)
    build_recommendations(report)

    print(report.render())
    return 1 if report.hard_blockers else 0


if __name__ == "__main__":
    raise SystemExit(run())
