# -*- coding: utf-8 -*-
"""ShoppingContext

用 ContextVar 保存当前任务的会话快照（shopping_session_id / buyer_id / locale / currency），
跨层透明传递：工具与子 Agent 执行时随时读取，无需层层透传参数。
多用户并发任务依赖 asyncio Task 级隔离，不会串台。
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from typing import Optional


@dataclass(frozen=True)
class ShoppingContextSnapshot:
    shopping_session_id: str
    buyer_id: str
    locale: str
    currency: str
    # 从长期 dislike 偏好推导出的结构化材质黑名单；工具入口会与模型入参取并集。
    excluded_material_tags: tuple[str, ...] = ()
    session_fence: int = 0
    prompt_version: str = ""
    prompt_variant: str = ""
    prompt_deployment_id: str = ""
    capability_digest: str = ""
    skill_catalog_mode: str = "legacy"
    prompt_document_json: str = field(default="", repr=False)
    model_snapshot: dict | None = None
    model_runtime: dict | None = field(default=None, repr=False)


_current_snapshot: ContextVar[Optional[ShoppingContextSnapshot]] = ContextVar(
    "globex_shopping_context",
    default=None,
)

# 工具可能在独立 asyncio Task 中执行，子任务内修改 ContextVar 不会回传父任务。
# 因此本轮偏好授权按买家+会话放在进程内临时表，由 orchestrator 在轮次边界清理。
_run_preference_activations: dict[tuple[str, str], tuple[tuple[tuple[str, str, str, int], ...], tuple[str, ...]]] = {}


class ShoppingContext:
    @staticmethod
    def set_model(snapshot: dict, runtime: dict) -> None:
        current = _current_snapshot.get()
        if current is None:
            raise RuntimeError("模型绑定需要当前会话上下文")
        _current_snapshot.set(replace(current, model_snapshot=snapshot, model_runtime=runtime))

    @staticmethod
    def set_skill_catalog_mode(mode: str) -> None:
        snapshot = _current_snapshot.get()
        if snapshot is None or mode not in {"legacy", "append_only"}:
            raise ValueError("Skill 注入模式或买家上下文无效")
        _current_snapshot.set(replace(snapshot, skill_catalog_mode=mode))

    @staticmethod
    def set(snapshot: ShoppingContextSnapshot):
        return _current_snapshot.set(snapshot)

    @staticmethod
    def reset(token) -> None:
        _current_snapshot.reset(token)

    @staticmethod
    def current() -> Optional[ShoppingContextSnapshot]:
        return _current_snapshot.get()

    @staticmethod
    def current_session_id() -> str:
        snapshot = _current_snapshot.get()
        return snapshot.shopping_session_id if snapshot else "anonymous"

    @staticmethod
    def set_excluded_material_tags(tags: list[str]) -> None:
        snapshot = _current_snapshot.get()
        if snapshot is None:
            return
        _current_snapshot.set(replace(snapshot, excluded_material_tags=tuple(dict.fromkeys(tags))))

    @staticmethod
    def activate_preferences(preferences: list[tuple[str, str, str, int]], excluded_material_tags: list[str]) -> None:
        snapshot = _current_snapshot.get()
        if snapshot is None:
            raise RuntimeError("偏好启用需要当前买家上下文")
        _run_preference_activations[(snapshot.buyer_id, snapshot.shopping_session_id)] = (
            tuple(preferences), tuple(dict.fromkeys(excluded_material_tags)),
        )

    @staticmethod
    def current_activated_preferences() -> tuple[tuple[str, str, str, int], ...]:
        snapshot = _current_snapshot.get()
        if snapshot is None:
            return ()
        return _run_preference_activations.get((snapshot.buyer_id, snapshot.shopping_session_id), ((), ()))[0]

    @staticmethod
    def current_activated_material_tags() -> tuple[str, ...]:
        snapshot = _current_snapshot.get()
        if snapshot is None:
            return ()
        return _run_preference_activations.get((snapshot.buyer_id, snapshot.shopping_session_id), ((), ()))[1]

    @staticmethod
    def clear_preference_activation(buyer_id: str, shopping_session_id: str) -> None:
        _run_preference_activations.pop((buyer_id, shopping_session_id), None)

    @staticmethod
    def set_session_fence(fence: int) -> None:
        snapshot = _current_snapshot.get()
        if snapshot is None:
            raise RuntimeError("不能为缺少当前上下文的会话设置 fence")
        _current_snapshot.set(replace(snapshot, session_fence=fence))

    @staticmethod
    def set_prompt_assignment(assignment: dict) -> None:
        import json
        snapshot = _current_snapshot.get()
        if snapshot is None:
            raise RuntimeError("Prompt 分组需要当前会话上下文")
        _current_snapshot.set(replace(snapshot, prompt_version=assignment["version_id"],
            prompt_variant=assignment["variant"], prompt_deployment_id=assignment["deployment_id"],
            prompt_document_json=json.dumps(assignment["document"], ensure_ascii=False)))

    @staticmethod
    def set_capability_digest(digest: str) -> None:
        snapshot = _current_snapshot.get()
        if snapshot is None:
            raise RuntimeError("能力版本绑定需要当前会话上下文")
        _current_snapshot.set(replace(snapshot, capability_digest=digest))
