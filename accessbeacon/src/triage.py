"""Explainable, deterministic accessibility triage; not a WCAG compliance audit."""

GUIDANCE = {
    "keyboard": ("2.1.1 Keyboard", "Reproduce the task without a mouse, restore keyboard operability, and verify visible focus and a logical tab sequence.", "Operability"),
    "screen-reader": ("4.1.2 Name, Role, Value", "Inspect accessible names, roles and states; correct semantic markup and test with a screen reader.", "Understandability"),
    "contrast": ("1.4.3 Contrast (Minimum)", "Measure foreground/background color contrast in every state and update design tokens, then retest.", "Perceivability"),
    "forms": ("3.3.2 Labels or Instructions", "Give each control a persistent programmatic label and provide actionable, connected error messages.", "Understandability"),
    "motion": ("2.3.3 Animation from Interactions", "Respect reduced-motion preferences and provide an alternative to nonessential motion.", "Perceivability"),
    "navigation": ("2.4.3 Focus Order", "Check headings, landmarks and focus sequence across the whole journey; preserve meaningful order.", "Operability"),
}
IMPACT = {"blocked": 90, "difficult": 65, "inconsistent": 35}

def classify(category, impact):
    if category not in GUIDANCE or impact not in IMPACT:
        raise ValueError("Unsupported category or impact")
    wcag, recommendation, principle = GUIDANCE[category]
    score = min(100, IMPACT[impact] + (5 if category in ("keyboard", "screen-reader", "forms") else 0))
    severity = "Critical" if score >= 90 else "High" if score >= 60 else "Moderate"
    reason = {
        "blocked": "A core task cannot be completed by at least one affected user.",
        "difficult": "A core task takes substantially more effort or creates avoidable errors.",
        "inconsistent": "The experience creates avoidable friction or inconsistent access.",
    }[impact]
    return {"priorityScore": score, "severity": severity, "wcag": wcag, "principle": principle,
            "recommendation": recommendation, "rationale": reason, "method": "transparent-rule-based-suggestion"}

def handler(event, _context):
    return classify(event["category"], event["impact"])
