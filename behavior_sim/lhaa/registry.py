"""YAML → LHAA-module factory.

Each peril is declared by a YAML spec in `configs/`. `load_module()` reads
one spec, resolves its `skill:` field to a concrete `LHAAInterface`
subclass (registered in `SKILL_REGISTRY`), wires up the four hook
callbacks, and returns a ready-to-execute module instance.

We keep skill imports lazy inside the registry to avoid a hard
dependency cycle: `interface.py` imports nothing from skills, and
skills import only from interface + hooks + budget + audit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .hooks import HOOK_REGISTRY, Hooks
from .interface import LHAAInterface

_CONFIGS_DIR = Path(__file__).parent / "configs"


# Skill name → loader function. Loaders are lazy so importing registry
# doesn't pull in attacker_agent / simulator unless actually needed.
def _load_closed_form_skill() -> type[LHAAInterface]:
    from .skill_closed_form import ClosedFormSkill

    return ClosedFormSkill


def _load_llm_attacker_skill() -> type[LHAAInterface]:
    from .skill_llm_attacker import LLMAttackerSkill

    return LLMAttackerSkill


SKILL_REGISTRY: dict[str, Any] = {
    "closed_form": _load_closed_form_skill,
    "llm_attacker": _load_llm_attacker_skill,
}


def list_configs() -> list[Path]:
    """All YAML configs, sorted for deterministic iteration."""
    return sorted(_CONFIGS_DIR.glob("lhaa_*.yaml"))


def load_spec(path: Path | str) -> dict:
    """Read and minimally validate a YAML spec."""
    p = Path(path)
    spec = yaml.safe_load(p.read_text())
    required = ("peril_id", "coverage_area", "paper_anchor", "skill", "threshold", "hooks", "budget")
    missing = [k for k in required if k not in spec]
    if missing:
        raise ValueError(f"{p.name}: missing required fields {missing}")
    if spec["skill"] not in SKILL_REGISTRY:
        raise ValueError(f"{p.name}: unknown skill {spec['skill']!r}")
    return spec


def _resolve_hooks(hooks_spec: dict[str, str]) -> Hooks:
    """Map hook name strings to callables from HOOK_REGISTRY."""
    def _r(name: str) -> Any:
        if name not in HOOK_REGISTRY:
            raise ValueError(f"unknown hook {name!r}")
        return HOOK_REGISTRY[name]
    return Hooks(
        pre_budget=_r(hooks_spec["pre_budget"]),
        pre_sandbox=_r(hooks_spec["pre_sandbox"]),
        post_audit=_r(hooks_spec["post_audit"]),
        post_verdict=_r(hooks_spec["post_verdict"]),
    )


def load_module(path: Path | str) -> LHAAInterface:
    """Instantiate a single LHAA module from its YAML config."""
    spec = load_spec(path)
    skill_cls = SKILL_REGISTRY[spec["skill"]]()
    budget_spec = spec["budget"]
    return skill_cls(
        peril_id=spec["peril_id"],
        coverage_area=spec["coverage_area"],
        threshold=float(spec["threshold"]),
        paper_anchor=spec["paper_anchor"],
        skill=spec["skill"],
        hooks=_resolve_hooks(spec["hooks"]),
        baseline=int(budget_spec.get("baseline", 100)),
        escalate_to=int(budget_spec.get("escalate_to", 300)),
        prior_fallback_enabled=(
            budget_spec.get("prior_fallback", "li_2024_table5") == "li_2024_table5"
        ),
    )


def load_all_modules() -> list[LHAAInterface]:
    """Load every YAML in configs/ as a module instance."""
    return [load_module(p) for p in list_configs()]


def load_stage1_modules() -> list[LHAAInterface]:
    """Closed-form modules (IA / II / III)."""
    return [m for m in load_all_modules() if m.skill == "closed_form"]


def load_stage2_modules() -> list[LHAAInterface]:
    """LLM-attacker modules (IV / AP1 / AP1.4 / AP3 / AP6)."""
    return [m for m in load_all_modules() if m.skill == "llm_attacker"]
