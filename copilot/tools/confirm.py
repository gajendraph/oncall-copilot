CONFIRM_TOKEN = "CONFIRM:"

def require_confirmation(proposed_cmd: str, user_reply: str | None):
    if not user_reply or not user_reply.strip().startswith(CONFIRM_TOKEN):
        return (False, f"Needs approval. Reply with '{CONFIRM_TOKEN} {proposed_cmd}' to proceed.")
    approved = user_reply.strip().removeprefix(CONFIRM_TOKEN).strip()
    return (approved == proposed_cmd, "Approved." if approved == proposed_cmd else "Mismatch. Not executing.")
