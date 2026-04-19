"""LLM 客户端 - 统一包装 OpenAI 兼容接口"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


@dataclass
class LLMConfig:
    api_key: str | None = None
    base_url: str | None = None
    planner_model: str = "gpt-4o"
    critic_model: str = "gpt-4o"
    vlm_model: str = "gpt-4o"

    @classmethod
    def from_env(cls) -> LLMConfig:
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            planner_model=os.getenv("PLANNER_MODEL", "gpt-4o"),
            critic_model=os.getenv("CRITIC_MODEL", "gpt-4o"),
            vlm_model=os.getenv("VLM_MODEL", "gpt-4o"),
        )


class LLMClient:
    """封装 chat / json_chat / vlm_chat 三种模式"""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()
        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def chat(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        temperature: float = 0.3,
    ) -> str:
        """普通文本对话"""
        resp = self._client.chat.completions.create(
            model=model or self.config.planner_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""

    def json_chat(
        self,
        system: str,
        user: str,
        *,
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """强制返回 JSON 对象"""
        resp = self._client.chat.completions.create(
            model=model or self.config.planner_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM 返回非法 JSON: {raw[:500]}") from e

    def vlm_chat(
        self,
        system: str,
        user: str,
        image_paths: list[str | Path],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        as_json: bool = True,
    ) -> dict[str, Any] | str:
        """多模态: 带图片的 chat, 用于 critic 看渲染截图"""
        content: list[dict[str, Any]] = [{"type": "text", "text": user}]
        for p in image_paths:
            path = Path(p)
            if not path.exists():
                continue
            b64 = base64.b64encode(path.read_bytes()).decode()
            suffix = path.suffix.lower().lstrip(".") or "png"
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{suffix};base64,{b64}",
                    },
                }
            )

        kwargs: dict[str, Any] = {
            "model": model or self.config.vlm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": temperature,
        }
        if as_json:
            kwargs["response_format"] = {"type": "json_object"}

        resp = self._client.chat.completions.create(**kwargs)
        raw = resp.choices[0].message.content or ""
        if as_json:
            try:
                return json.loads(raw or "{}")
            except json.JSONDecodeError as e:
                raise ValueError(f"VLM 返回非法 JSON: {raw[:500]}") from e
        return raw
