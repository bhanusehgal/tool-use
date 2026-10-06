"""Stage 4 switches. Every fix can be turned on and off on its own, so the eval
harness can measure what each one contributes (an "ablation").

All switches off = the original behaviour, so the stage 3 baseline stays reproducible.
"""

STEMMING = False       # Fix 1: "meals" matches "meal" in keyword search
PROMPT_RULES = False   # Fix 2: grounding + planning rules in the system prompt
BETTER_ERRORS = False  # Fix 3: stage 1 errors quote the mistake and show the fix; one retry nudge
JSON_MODE = False      # Fix 4: stage 1 asks Ollama for constrained JSON output
CLAIM_GUARD = False    # Fix 5: send back answers that claim actions no tool performed
RETRIEVAL = "keyword"  # Stage 5: "keyword" | "semantic" | "hybrid"  (how search_documents finds text)

SWITCHES = ["STEMMING", "PROMPT_RULES", "BETTER_ERRORS", "JSON_MODE", "CLAIM_GUARD"]

VARIANTS = {
    "baseline": [],
    "stemming": ["STEMMING"],
    "prompt": ["PROMPT_RULES"],
    "errors": ["BETTER_ERRORS"],
    "json": ["JSON_MODE"],
    "guard": ["CLAIM_GUARD"],
    "all": SWITCHES,
    # stage 5: retrieval modes (entries like "RETRIEVAL=hybrid" set a value instead of turning a switch on)
    "semantic": ["RETRIEVAL=semantic"],
    "hybrid": ["RETRIEVAL=hybrid"],
    "all_hybrid": SWITCHES + ["RETRIEVAL=hybrid"],
    "all_semantic": SWITCHES + ["RETRIEVAL=semantic"],
}
# Variants that only change stage 1's protocol; running them on stage 2 would just repeat the baseline.
STAGE1_ONLY = {"errors", "json"}

PROMPT_RULES_TEXT = (
    "\n\nRULES:\n"
    "1. Numbers from company policy (raise percentages, allowances, vacation accrual, prices, discounts) "
    "must come from search_documents. Never assume them or use 'typical' values.\n"
    "2. For questions with several parts: first work out which facts you need, fetch each one with a tool, "
    "then do the maths with ONE calculate call that includes every factor.\n"
    "3. Before giving your final answer, check that every number in it came from a tool result or a calculation."
)


def apply_variant(name: str) -> None:
    if name not in VARIANTS:
        raise ValueError(f"Unknown variant '{name}'. Choose from: {', '.join(VARIANTS)}")
    for switch in SWITCHES:
        globals()[switch] = switch in VARIANTS[name]
    global RETRIEVAL
    RETRIEVAL = "keyword"
    for entry in VARIANTS[name]:
        if entry.startswith("RETRIEVAL="):
            RETRIEVAL = entry.split("=", 1)[1]


def active() -> list[str]:
    on = [s for s in SWITCHES if globals()[s]]
    return on + ([f"RETRIEVAL={RETRIEVAL}"] if RETRIEVAL != "keyword" else [])
