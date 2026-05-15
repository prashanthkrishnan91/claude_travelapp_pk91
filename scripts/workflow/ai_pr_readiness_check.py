#!/usr/bin/env python3
"""AI PR Readiness Gate — structural pre-merge checker.

stdlib only, no network calls, no external dependencies.

Exit 0 = pass (warnings may exist).
Exit 1 = hard failure(s) found.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

LEDGER_PATH = "docs/ai/USAGE_LEDGER.md"

# Matches any wording in the PR body that claims usage is durably tracked.
USAGE_CLAIM_RE = re.compile(
    r"usage\s+(?:tracked|ledger\s+updated|ledger\s*(?:.*?)(?:yes|committed))|"
    r"usage\s+ledger\s+row\s*[:\-]\s*(?:committed|yes|updated)|"
    r"usage\s+ledger\s*[:\-]\s*(?:committed|yes|updated)|"
    r"see\s+(?:docs/ai/)?usage[_\s\-]?ledger|"
    r"ledger\s+updated\s*[:\-]?\s*yes|"
    r"ledger\s+row\s*[:\-]\s*(?:committed|yes)",
    re.IGNORECASE,
)

UNAVAILABLE_RE = re.compile(
    r"unavailable|not\s+available|tooling.*unavailable",
    re.IGNORECASE,
)

PR_BODY_REQUIRED = [
    "## Summary",
    "## Severity",
    "## Validation",
    "SQL / env / providers / UI",
    "AI usage note",
    "AI PR readiness",
]

USAGE_METADATA_FIELDS = [
    "Usage ledger row",
    "Prompt ID",
    "Model",
    "Chat strategy",
    "Main token drivers",
    "Waste classification",
    "Follow-up count",
]

RUNTIME_RE = re.compile(
    r"production|railway|worker|persistence|cache\b|provider|"
    r"api\s+mismatch|live\s+validation|refresh\s+job|stale\s+data|\bruntime\b",
    re.IGNORECASE,
)

# Template-only runtime phrases that should not trigger the runtime gate.
RUNTIME_TEMPLATE_ONLY_RE = re.compile(
    r"runtime.{0,30}validation.{0,30}note|runtime.{0,30}n/a|no\s+runtime\s+or\s+design",
    re.IGNORECASE,
)

DESIGN_FILE_RE = re.compile(
    r"design.?system|globals\.css|tailwind\.config|app.?shell|design.?bible",
    re.IGNORECASE,
)

DESIGN_BODY_RE = re.compile(
    r"design\s+overhaul|wife.?wow|visual\s+transformation|design-system",
    re.IGNORECASE,
)

PRODUCT_CODE_RE = re.compile(
    r"^(src|app|pages|components|lib|api|backend|frontend|v2)/",
    re.IGNORECASE,
)

WORKFLOW_ONLY_RE = re.compile(
    r"^(docs/|\.github/|\.claude/|CLAUDE\.md$|scripts/)",
    re.IGNORECASE,
)

DEPENDENCY_RE = re.compile(
    r"(package\.json|package-lock\.json|yarn\.lock|requirements\.txt|"
    r"Pipfile|pyproject\.toml|\d+.*\.sql|migration|railway\.toml|vercel\.json)$",
    re.IGNORECASE,
)

ENV_FILE_RE = re.compile(r"^\.env$|^\.env\.", re.IGNORECASE)
# Templates (.env.example, .env.sample, .env.template, .env.dist) should warn, not hard-fail.
ENV_TEMPLATE_RE = re.compile(r"\.(example|sample|template|dist)$", re.IGNORECASE)
UI_FILE_RE = re.compile(r"\.(tsx|jsx|html|css|vue)$", re.IGNORECASE)


def _run(cmd: List[str]) -> Optional[str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def changed_files(base_ref: str) -> Optional[List[str]]:
    out = _run(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
    if out is None:
        return None
    return [f.strip() for f in out.splitlines() if f.strip()]


def diff_stat(base_ref: str) -> Optional[Tuple[int, int]]:
    out = _run(["git", "diff", "--shortstat", f"{base_ref}...HEAD"])
    if not out:
        return None
    m_add = re.search(r"(\d+) insertion", out)
    m_del = re.search(r"(\d+) deletion", out)
    return (int(m_add.group(1)) if m_add else 0, int(m_del.group(1)) if m_del else 0)


def read_pr_body(pr_body_file: Optional[str], event_path: Optional[str]) -> Optional[str]:
    if pr_body_file and Path(pr_body_file).exists():
        return Path(pr_body_file).read_text(encoding="utf-8", errors="replace")
    if event_path and Path(event_path).exists():
        try:
            data = json.loads(Path(event_path).read_text(encoding="utf-8"))
            return data.get("pull_request", {}).get("body") or ""
        except Exception:
            pass
    return None


def detect_level(body: Optional[str]) -> int:
    if not body:
        return 1
    m = re.search(r"level[:\s]*([0-3])", body, re.IGNORECASE)
    return int(m.group(1)) if m else 1


def ledger_changed(files: Optional[List[str]]) -> bool:
    if files is None:
        return False
    return any(LEDGER_PATH in f or f == LEDGER_PATH for f in files)


def claims_usage(body: str) -> bool:
    return bool(USAGE_CLAIM_RE.search(body))


def says_unavailable(body: str) -> bool:
    return bool(UNAVAILABLE_RE.search(body))


def ledger_has_data_row(text: str) -> bool:
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and "---" not in s and s.count("|") >= 3):
            continue
        if "PR" in s and ("Prompt" in s or "Phase" in s) and "Model" in s:
            continue
        if s and s != "|" and "template row" not in s.lower():
            return True
    return False


def files_match(files: List[str], pattern: "re.Pattern[str]") -> bool:
    return any(pattern.search(f) for f in files)


def is_product_pr(files: List[str]) -> bool:
    return files_match(files, PRODUCT_CODE_RE)


def is_workflow_only(files: List[str]) -> bool:
    return all(WORKFLOW_ONLY_RE.search(f) for f in files)


class Checker:
    def __init__(
        self,
        base_ref: str = "main",
        body: Optional[str] = None,
        level: Optional[int] = None,
        allow_no_ledger: bool = False,
        warn_only: bool = False,
        fmt: str = "text",
    ) -> None:
        self.base_ref = base_ref
        self.body = body or ""
        self._level_override = level
        self.allow_no_ledger = allow_no_ledger
        self.warn_only = warn_only
        self.fmt = fmt
        self.files: Optional[List[str]] = None
        self.git_ok = True
        self.ledger_text: Optional[str] = None
        self.fails: List[str] = []
        self.warns: List[str] = []

    @property
    def level(self) -> int:
        if self._level_override is not None:
            return self._level_override
        return detect_level(self.body)

    def _fail(self, msg: str) -> None:
        if self.warn_only:
            self.warns.append("[warn-only] " + msg)
        else:
            self.fails.append(msg)

    def _warn(self, msg: str) -> None:
        self.warns.append(msg)

    def gather(self) -> None:
        self.files = changed_files(self.base_ref)
        if self.files is None:
            self.git_ok = False
            self._warn(
                "Could not determine changed files (git diff unavailable). Running partial checks only."
            )
        p = Path(LEDGER_PATH)
        self.ledger_text = p.read_text(encoding="utf-8", errors="replace") if p.exists() else None

    # A — Usage ledger enforcement
    def check_ledger(self) -> None:
        lchanged = ledger_changed(self.files)
        needs_ledger = self.level >= 1 or (
            self.files is not None
            and (is_product_pr(self.files) or not is_workflow_only(self.files))
        )
        is_docs_only = (
            self.files is not None
            and all(f.startswith("docs/") or f.startswith(".github/") or f in ("CLAUDE.md", "README.md")
                    for f in self.files)
        )

        if needs_ledger and not self.allow_no_ledger:
            if self.files is not None and not lchanged:
                if self.level == 0 and is_docs_only:
                    # Level 0 docs-only PRs may skip ledger
                    return
                # Level 1+ PRs must commit a ledger row, even if token values are unavailable.
                # "Usage unavailable" marks token/delta fields unavailable, but the row itself must exist.
                self._fail(
                    f"Level {self.level} PR must change {LEDGER_PATH}. "
                    "Commit a sanitized manual row with metadata fields and token/delta fields marked unavailable, or use --allow-no-ledger with documented reason."
                )
            elif self.files is None:
                self._warn(
                    f"Cannot verify {LEDGER_PATH} was updated (git unavailable). "
                    "Ensure a ledger row is committed for Level 1+ PRs."
                )

        if claims_usage(self.body) and self.files is not None and not lchanged:
            self._fail(
                f"PR body claims usage is tracked but {LEDGER_PATH} was not changed. "
                "Remove the claim or commit the ledger row."
            )

        if lchanged and self.ledger_text and not ledger_has_data_row(self.ledger_text):
            self._warn(f"{LEDGER_PATH} changed but no substantive data row found.")

        if "pending-pr" in self.body.lower():
            self._warn("PR body contains 'pending-pr' — replace with actual PR number before merge.")

        if lchanged and self.ledger_text:
            recent = [ln for ln in self.ledger_text.splitlines()[-20:] if ln.startswith("|")]
            if any("unknown" in ln.lower() for ln in recent):
                self._warn(
                    "Newest ledger row has 'unknown' value(s). "
                    "Fill model, chat strategy, main drivers, waste classification if available."
                )

    # B — PR body required sections
    def check_sections(self) -> None:
        if not self.body:
            self._warn("No PR body provided — skipping section checks.")
            return
        for sec in PR_BODY_REQUIRED:
            if sec.lower() not in self.body.lower():
                self._fail(f"PR body missing required section/anchor: '{sec}'")

    # C — Usage metadata fields
    def check_metadata(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        for field in USAGE_METADATA_FIELDS:
            if field.lower() not in bl:
                self._warn(f"PR body missing usage metadata field: '{field}'")

    # D — Scope and validation
    def check_scope(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        if self.files and is_product_pr(self.files):
            m = re.search(r"## validation(.*?)(?=##|\Z)", self.body, re.DOTALL | re.IGNORECASE)
            if m and len(m.group(1).strip()) < 20:
                self._warn("Product code changed but Validation section is very short.")
        if self.files and files_match(self.files, UI_FILE_RE):
            if not any(k in bl for k in ("screenshot", "ui validation", "visual")):
                self._warn("UI files changed but no screenshot/UI validation note found.")
        if re.search(r"full suite|all tests|run all", bl):
            if not re.search(r"because|reason|justif", bl):
                self._warn("Full test suite claimed — include justification for why broader tier was needed.")

    # E — Runtime/production fix gate
    def check_runtime(self) -> None:
        if not self.body or not RUNTIME_RE.search(self.body):
            return
        # Workflow-only PRs are exempt: the PR template's "Runtime/design validation note" section
        # header contains the word "runtime" and should not trigger this gate.
        if self.files is not None and is_workflow_only(self.files):
            return
        # Skip if the only runtime mentions are template-placeholder phrases.
        body_stripped = RUNTIME_TEMPLATE_ONLY_RE.sub("", self.body)
        if not RUNTIME_RE.search(body_stripped):
            return
        bl = self.body.lower()
        has_evidence = any(k in bl for k in (
            "runtime validation", "failure-seam", "failure seam",
            "log key", "reproduction", "exact boundary",
        ))
        if not has_evidence:
            self._fail(
                "PR references production/runtime/provider but lacks runtime validation "
                "or failure-seam evidence (log key, test name, reproduction step, exact boundary)."
            )
        if re.search(r"\bsymptom\b|\bworkaround\b|patch.*around", bl):
            if not any(k in bl for k in ("root cause", "exact boundary", "failure seam", "failing seam")):
                self._warn("PR may describe symptom patching — ensure root cause / failure-seam evidence is present.")

    # F — Design transformation gate
    def check_design(self) -> None:
        if not self.body:
            return
        is_design = (self.files and files_match(self.files, DESIGN_FILE_RE)) or bool(DESIGN_BODY_RE.search(self.body))
        if not is_design:
            return
        bl = self.body.lower()
        if not any(k in bl for k in ("foundation-only", "visible adoption", "polish")):
            self._fail("Design PR must classify scope: 'foundation-only', 'visible adoption', or 'polish'.")
        if any(k in bl for k in ("visual transformation", "wife-wow")) and "foundation-only" not in bl:
            if not any(k in bl for k in ("screenshot", "ui validation")):
                self._fail(
                    "PR claims visual transformation but no screenshot/UI validation "
                    "and not classified as 'foundation-only'."
                )
        if re.search(r"\bmotion\b|\bgradient\b|\bglass\b|\blur\b", bl):
            if not any(k in bl for k in ("accessibility", "reduced-motion", "contrast")):
                self._warn("PR adds motion/gradients/glass — include reduced-motion/accessibility/contrast note.")

    # G — Same-chat / context budget
    def check_same_chat(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        if "same-chat" not in bl and "same chat" not in bl:
            return
        m = re.search(r"follow.up count[:\s]*(\d+)", bl)
        if m and int(m.group(1)) > 1:
            self._warn(f"Same-chat follow-up count {m.group(1)} — consider fresh chat for next PR.")
        if re.search(r"production|debug.*loop|runtime.*loop", bl):
            self._warn("Same-chat used for production/debug loop — prefer fresh chat for debugging.")
        if re.search(r"new.*slice|different.*feature|unrelated", bl):
            self._warn("Same-chat possibly used for new unrelated slice — fresh chat is default for new PRs.")

    # H — Patch exhaustion
    def check_patch_exhaustion(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        m = re.search(r"follow.up(?:\s+patches?)?(?:\s+count)?[:\s]*(\d+)", bl)
        count = int(m.group(1)) if m else 0
        if count >= 3:
            has_note = any(k in bl for k in (
                "fresh-chat escalation", "full-plumbing analysis", "continuing is safe",
            ))
            if not has_note:
                self._fail(
                    f"Follow-up count {count} (>=3). Add a 'fresh-chat escalation note' or "
                    "'full-plumbing analysis note' explaining why continuation is safe."
                )
        elif count == 2:
            if not re.search(r"fresh.chat|full.plumbing|escalation", bl):
                self._warn(
                    "Follow-up count 2 — include a fresh-chat escalation or full-plumbing analysis note."
                )

    # I — Model routing / reviewer gate
    def check_model_routing(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        is_risky = self.level >= 2 or bool(re.search(
            r"production|finance.*decision|provider|persistence|major\s+ui|architecture", bl,
        ))
        if is_risky:
            has_reviewer = any(k in bl for k in (
                "reviewer", "fresh-context", "targeted audit", "reviewer skipped", "no reviewer",
            ))
            if not has_reviewer:
                self._warn(
                    f"Level {self.level}/risky PR lacks a targeted fresh-context reviewer note "
                    "or explicit 'no reviewer — <reason>'."
                )
        if "opus" in bl and not re.search(r"architecture|root.cause|complex", bl):
            self._warn("Opus used without architecture/root-cause justification — Sonnet is the default.")

    # J — Subagent discipline
    def check_subagents(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        if re.search(r"subagent|sub.agent|multiple\s+agent|parallel\s+agent", bl):
            if not re.search(r"findings|bounded|read.only|context.protect", bl):
                self._warn(
                    "Multiple/parallel agents mentioned — ensure bounded read-only use with concise findings."
                )
            if self.level <= 1:
                self._warn("Subagent fan-out mentioned for Level 1 work — prefer single-agent.")

    # K — Test discipline
    def check_tests(self) -> None:
        if not self.body:
            return
        bl = self.body.lower()
        if self.level >= 1 and not any(k in bl for k in ("tier", "test tier", "test bundle", "test:")):
            self._warn("PR body does not mention test tier — specify tier used and why sufficient.")
        if re.search(r"full suite|all tests|run all", bl):
            if not re.search(r"because|reason|justif|fail", bl):
                self._warn("Full test suite claimed — include justification.")
        if self.files and files_match(self.files, UI_FILE_RE):
            if not any(k in bl for k in ("screenshot", "visual", "manual ui")):
                self._warn("UI files changed — include screenshot, visual, or manual UI validation note.")

    # L — CLAUDE.md context-debt gate
    def check_claude_md(self) -> None:
        p = Path("CLAUDE.md")
        if not p.exists():
            return
        lines = len(p.read_text(encoding="utf-8").splitlines())
        if lines > 200:
            touched = self.files is not None and "CLAUDE.md" in self.files
            if touched:
                self._warn(
                    f"CLAUDE.md is {lines} lines (budget: 200). "
                    "Move enforcement details into scripts/templates/hooks rather than growing CLAUDE.md."
                )
            else:
                self._warn(f"CLAUDE.md is {lines} lines (over 200-line budget). Compact when next touched.")

    # M — Safety scaffolds documented
    def check_safety_hook(self) -> None:
        gate_doc = Path("docs/ai/AI_PR_READINESS_GATE.md")
        hook = Path(".claude/hooks/ai_pr_readiness_stop.sh")
        if gate_doc.exists() and not hook.exists():
            self._warn("AI_PR_READINESS_GATE.md exists but .claude/hooks/ai_pr_readiness_stop.sh not found.")
        danger_doc = Path("docs/ai/DANGEROUS_ACTION_GUARD.md")
        danger_hook = Path(".claude/hooks/dangerous_action_guard.sh")
        if danger_doc.exists() and not danger_hook.exists():
            self._warn("DANGEROUS_ACTION_GUARD.md exists but .claude/hooks/dangerous_action_guard.sh not found.")
        if danger_hook.exists() and not danger_doc.exists():
            self._warn("dangerous_action_guard.sh exists but docs/ai/DANGEROUS_ACTION_GUARD.md not found.")

    # N — Dependency/migration/env changes
    def check_deps(self) -> None:
        if self.files is None or not self.body:
            return
        # Raw env files hard-fail; documented templates (.env.example etc.) only warn.
        raw_env = [f for f in self.files if ENV_FILE_RE.search(f) and not ENV_TEMPLATE_RE.search(f)]
        env_templates = [f for f in self.files if ENV_FILE_RE.search(f) and ENV_TEMPLATE_RE.search(f)]
        if raw_env:
            self._fail(f"Committed .env/secrets file detected: {', '.join(raw_env)}. Remove immediately.")
        if env_templates:
            self._warn(
                f"Env template file(s) committed ({', '.join(env_templates[:2])}). "
                "Verify they contain only placeholder values, not real secrets."
            )
        dep_files = [f for f in self.files if DEPENDENCY_RE.search(f)]
        if dep_files:
            bl = self.body.lower()
            if not re.search(r"why|reason|need|requir|introduc", bl):
                self._warn(
                    f"Dependency/migration/env files changed ({', '.join(dep_files[:3])}) — "
                    "explain why the change is needed."
                )
            if any("migration" in f.lower() or f.endswith(".sql") for f in dep_files):
                if "rollback" not in bl:
                    self._warn("Migration/SQL file changed — include a rollback plan.")

    # O — PR size budget
    def check_size(self) -> None:
        if self.files is None:
            return
        n = len(self.files)
        stat = diff_stat(self.base_ref)
        lines = sum(stat) if stat else None
        lv = self.level
        if lv <= 1:
            if n > 8:
                self._warn(f"Level {lv} PR changes {n} files (soft limit: 8). Explain scope or split.")
            if lines and lines > 400:
                self._warn(f"Level {lv} PR ~{lines} added+deleted lines (soft limit: 400). Consider splitting.")
        elif lv == 2:
            if n > 20:
                self._warn(f"Level 2 PR changes {n} files (soft limit: 20). Include split justification.")
            if lines and lines > 1200:
                self._warn(f"Level 2 PR ~{lines} added+deleted lines (soft limit: 1200).")
        families: set = set()
        for f in self.files:
            if re.search(r"^(src|app|pages|components|frontend|v2/frontend)/", f):
                families.add("frontend")
            if re.search(r"^(backend|api|v2/backend|lib)/", f):
                families.add("backend")
            if f.startswith("docs/"):
                families.add("docs")
            if re.search(r"^(scripts/|\.github/|\.claude/|CLAUDE\.md)", f):
                families.add("workflow")
            if re.search(r"migration|\.sql$", f):
                families.add("sql")
        if len(families) >= 4:
            self._warn(f"PR mixes {', '.join(sorted(families))} — add scope explanation or consider splitting.")

    def run(self) -> int:
        self.gather()
        self.check_ledger()
        if self.body:
            self.check_sections()
            self.check_metadata()
            self.check_scope()
            self.check_runtime()
            self.check_design()
            self.check_same_chat()
            self.check_patch_exhaustion()
            self.check_model_routing()
            self.check_subagents()
            self.check_tests()
        self.check_claude_md()
        self.check_safety_hook()
        self.check_deps()
        self.check_size()
        return self._report()

    def _report(self) -> int:
        exit_code = 1 if self.fails else 0
        if self.fmt == "json":
            # JSON mode: clean JSON only, no text output before it.
            print(json.dumps(self.result_json(), indent=2))
            return exit_code
        # Text mode
        if not self.fails and not self.warns:
            print("✅ AI PR Readiness: PASS")
            return 0
        if self.fails:
            print(f"❌ AI PR Readiness: FAIL — {len(self.fails)} hard failure(s)\n")
            for i, f in enumerate(self.fails, 1):
                print(f"  FAIL {i}: {f}")
            if self.warns:
                print()
        else:
            print(f"⚠️  AI PR Readiness: PASS WITH WARNINGS — {len(self.warns)} warning(s)\n")
        if self.warns:
            for i, w in enumerate(self.warns, 1):
                print(f"  WARN {i}: {w}")
        if self.fails:
            print("\nFix hard failure(s) before opening/updating this PR.")
        else:
            print("\nWarnings are advisory. Resolve before merge when practical.")
        return exit_code

    def result_json(self) -> dict:
        return {
            "pass": not bool(self.fails),
            "hard_failures": self.fails,
            "warnings": self.warns,
            "level": self.level,
            "git_available": self.git_ok,
        }


def run_self_tests() -> int:
    errors = 0

    def eq(name: str, got: object, exp: object) -> None:
        nonlocal errors
        if got != exp:
            print(f"  FAIL {name}: got {got!r}, expected {exp!r}")
            errors += 1
        else:
            print(f"  pass {name}")

    # Usage claim detection
    eq("claims_usage_tracked", claims_usage("Usage tracked: yes"), True)
    eq("claims_ledger_updated", claims_usage("Usage ledger updated: Yes"), True)
    eq("claims_no_info", claims_usage("No usage info"), False)
    eq("claims_ledger_row_committed", claims_usage("Usage ledger row: committed"), True)
    eq("claims_ledger_row_yes", claims_usage("Usage ledger row: yes"), True)
    eq("claims_ledger_committed", claims_usage("Usage ledger: committed"), True)
    eq("claims_see_ledger_md", claims_usage("see docs/ai/USAGE_LEDGER.md"), True)
    eq("claims_see_usage_ledger", claims_usage("see usage ledger"), True)
    eq("claims_ledger_row_prefix", claims_usage("ledger row: committed"), True)
    # Ledger change detection
    eq("ledger_changed_yes", ledger_changed(["docs/ai/USAGE_LEDGER.md", "CLAUDE.md"]), True)
    eq("ledger_changed_no", ledger_changed(["CLAUDE.md"]), False)
    eq("ledger_changed_none", ledger_changed(None), False)
    # Level detection
    eq("detect_level_0", detect_level("Level: 0"), 0)
    eq("detect_level_2", detect_level("Level: 2"), 2)
    eq("detect_level_default", detect_level("no info"), 1)
    # Product/workflow classification
    eq("product_code_src", is_product_pr(["src/components/Foo.tsx"]), True)
    eq("product_code_v2", is_product_pr(["v2/frontend/pages/index.tsx"]), True)
    eq("product_code_docs", is_product_pr(["docs/ai/HANDOFF.md"]), False)
    eq("workflow_only_yes", is_workflow_only(["docs/ai/HANDOFF.md", "CLAUDE.md"]), True)
    eq("workflow_only_no", is_workflow_only(["src/app.tsx", "docs/ai/HANDOFF.md"]), False)
    # Unavailable detection
    eq("says_unavailable_yes", says_unavailable("Usage ledger row: unavailable — no tooling"), True)
    eq("says_unavailable_no", says_unavailable("everything is fine"), False)
    # Env file / template classification
    eq("env_file_re_env", bool(ENV_FILE_RE.search(".env")), True)
    eq("env_file_re_env_local", bool(ENV_FILE_RE.search(".env.local")), True)
    eq("env_file_re_env_prod", bool(ENV_FILE_RE.search(".env.production")), True)
    eq("env_template_re_example", bool(ENV_TEMPLATE_RE.search(".env.example")), True)
    eq("env_template_re_sample", bool(ENV_TEMPLATE_RE.search(".env.sample")), True)
    eq("env_template_re_dist", bool(ENV_TEMPLATE_RE.search(".env.dist")), True)
    eq("env_template_re_non_env", bool(ENV_TEMPLATE_RE.search("config.py")), False)

    # Ledger enforcement tests (strict mode) — these test the logic directly
    print("\n  === Ledger enforcement logic tests ===")
    # Test: Level 1 + no ledger change = should require ledger
    c1 = Checker(body="Level: 1", level=1, allow_no_ledger=False)
    c1.files = ["src/app.tsx"]
    c1.check_ledger()
    eq("Level1_no_ledger_fails", bool(c1.fails), True)

    # Test: Level 1 + ledger changed = should pass
    c2 = Checker(body="Level: 1", level=1)
    c2.files = ["src/app.tsx", "docs/ai/USAGE_LEDGER.md"]
    c2.check_ledger()
    eq("Level1_ledger_changed_passes", bool(c2.fails), False)

    # Test: Level 0 docs-only + no ledger = should pass
    c3 = Checker(body="Level: 0", level=0)
    c3.files = ["docs/ai/HANDOFF.md", "CLAUDE.md"]
    c3.check_ledger()
    eq("Level0_docsonly_no_ledger_passes", bool(c3.fails), False)

    # Test: Level 0 mixed with product code + no ledger = should fail
    c4 = Checker(body="Level: 0", level=0)
    c4.files = ["docs/ai/HANDOFF.md", "src/app.tsx"]
    c4.check_ledger()
    eq("Level0_mixed_no_ledger_fails", bool(c4.fails), True)

    # Test: claims usage tracked + no ledger = should fail
    c5 = Checker(body="Usage ledger row: committed", level=1)
    c5.files = ["src/app.tsx"]
    c5.check_ledger()
    eq("claims_tracked_no_ledger_fails", bool(c5.fails), True)

    # Test: claims usage tracked + ledger changed = should pass
    c6 = Checker(body="Usage ledger row: committed", level=1)
    c6.files = ["src/app.tsx", "docs/ai/USAGE_LEDGER.md"]
    c6.check_ledger()
    eq("claims_tracked_ledger_changed_passes", bool(c6.fails), False)

    # Test: allow_no_ledger flag bypasses requirement
    c7 = Checker(body="Level: 1", level=1, allow_no_ledger=True)
    c7.files = ["src/app.tsx"]
    c7.check_ledger()
    eq("allow_no_ledger_flag_passes", bool(c7.fails), False)

    if errors == 0:
        print("All self-tests passed.")
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description="AI PR Readiness Gate (stdlib only, no network).")
    p.add_argument("--base-ref", default="main", help="Git base ref for diff (default: main)")
    p.add_argument("--pr-body-file", help="Path to file containing PR body text")
    p.add_argument("--github-event-path", help="Path to GitHub Actions event JSON")
    p.add_argument("--level", type=int, choices=[0, 1, 2, 3], help="Override PR level")
    p.add_argument("--allow-no-ledger", action="store_true", help="Skip ledger check (Level 0/docs-only)")
    p.add_argument("--warn-only", action="store_true", help="Downgrade hard failures to warnings")
    p.add_argument("--format", choices=["text", "json"], default="text", dest="fmt",
                   help="Output format. json emits clean JSON only with no preceding text.")
    p.add_argument("--self-test", action="store_true", help="Run internal self-tests")
    args = p.parse_args()

    if args.self_test:
        return run_self_tests()

    body = read_pr_body(args.pr_body_file, args.github_event_path)
    checker = Checker(
        base_ref=args.base_ref,
        body=body,
        level=args.level,
        allow_no_ledger=args.allow_no_ledger,
        warn_only=args.warn_only,
        fmt=args.fmt,
    )
    return checker.run()


if __name__ == "__main__":
    raise SystemExit(main())
