from copilot.agent import Agent

TEMPLATE = (
    "You are an SRE drafting a concise stakeholder update. Keep under 600 characters.\n"
    "Include:\n"
    "- Impact (who/what is affected)\n"
    "- Scope (duration/regions/services)\n"
    "- Action (what's being done)\n"
    "- Next update time (if unknown, say 'TBD')\n\n"
    "Given this context:\n{context}\n\n"
    "Write the update in one short paragraph (no PII)."
)

def status_from_context(context: str) -> str:
    a = Agent()
    msg = TEMPLATE.format(context=context)
    return a.chat([{"role":"user","content": msg}])
