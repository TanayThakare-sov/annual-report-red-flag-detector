"""Thin wrapper so the rest of the app is independent of the LLM provider."""
import json
import os
import re
import time

from src import config


def extract_json(text: str) -> dict:
    """Parse JSON from a model reply, tolerating code fences and stray prose."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.M).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        return json.loads(t[start : end + 1])
    raise ValueError("Model did not return valid JSON")


class LLM:
    def __init__(self, provider: str = "anthropic", model: str = None, api_key: str = None):
        if provider not in config.DEFAULT_MODELS:
            raise ValueError(f"Unknown provider: {provider}")
        self.provider = provider
        self.model = model or config.DEFAULT_MODELS[provider]
        key = api_key or os.getenv(config.ENV_KEYS[provider])
        if not key:
            raise ValueError(
                f"No API key for {provider}. Paste it in the sidebar or set {config.ENV_KEYS[provider]} in .env"
            )
        self._client = self._make_client(key)

    def _make_client(self, key: str):
        if self.provider == "anthropic":
            import anthropic

            return anthropic.Anthropic(api_key=key)
        if self.provider == "openai":
            from openai import OpenAI

            return OpenAI(api_key=key)
        from google import genai

        return genai.Client(api_key=key)

    def _call(self, system: str, user: str, max_tokens: int, json_mode: bool) -> str:
        if self.provider == "anthropic":
            r = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")

        if self.provider == "openai":
            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            r = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_completion_tokens=max_tokens,
                **kwargs,
            )
            return r.choices[0].message.content or ""

        from google.genai import types

        cfg = types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens * 2,  # Gemini 2.5 "thinking" shares this budget
            temperature=0.1,
            response_mime_type="application/json" if json_mode else None,
        )
        r = self._client.models.generate_content(model=self.model, contents=user, config=cfg)
        return r.text or ""

    def complete(self, system: str, user: str, max_tokens: int = 4096, json_mode: bool = False) -> str:
        last = None
        for attempt in range(3):
            try:
                return self._call(system, user, max_tokens, json_mode)
            except Exception as e:  # network / rate-limit errors
                last = e
                time.sleep(2**attempt)
        raise RuntimeError(f"LLM call failed after retries: {last}")

    def complete_json(self, system: str, user: str, max_tokens: int = 4096) -> dict:
        return extract_json(self.complete(system, user, max_tokens, json_mode=True))
