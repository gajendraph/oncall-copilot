import os
from typing import List, Dict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
MODEL = os.getenv("MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class Agent:
    def __init__(self, system_prompt: str = "You are a helpful SRE copilot. Prefer tools for facts."):
        self.system_prompt = system_prompt

    def chat(self, messages: List[Dict[str, str]]) -> str:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role":"system","content": self.system_prompt}] + messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content
