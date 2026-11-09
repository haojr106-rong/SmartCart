# -*- coding: utf-8 -*-
"""买家批准后，仅在当前运行中启用已召回的长期偏好。"""
import json

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk

from app.application.memory.preference_selector import material_exclusion_tags, render_preference_hint
from app.infrastructure.context import ShoppingContext


def build_activate_preferences_tool(store, bus):
    async def activate_preferences_tool(
        memory_ids: list[str],
        expected_versions: list[int],
        statements: list[str],
    ) -> ToolChunk:
        """申请买家确认，将相关长期偏好用于本轮具体商品检索、比较或推荐。

        不适用于商品知识、参数解释、价格带或避坑问答。批准只影响本轮，不修改长期偏好。

        Args:
            memory_ids: preference-candidates 中候选的稳定 ID，顺序与 statements 一致。
            expected_versions: 对应候选的版本号。
            statements: 对应候选的完整原文，用于确认卡向买家展示。
        """
        ctx = ShoppingContext.current()
        if ctx is None:
            return ToolChunk(content=[TextBlock(text="[error] 缺少买家上下文")], state=ToolResultState.ERROR)
        bus.publish(ctx.shopping_session_id, "tool.invoke", {"tool": "activate_preferences_tool",
            "args": {"memory_ids": memory_ids, "expected_versions": expected_versions, "statements": statements}})
        current = await store.list_by_buyer(ctx.buyer_id)
        indexed = {(p.memory_id, p.version, p.statement): p for p in current}
        keys = list(zip(memory_ids, expected_versions, statements))
        selected = [indexed[key] for key in keys if key in indexed]
        if not keys or len(selected) != len(keys) or len({p.memory_id for p in selected}) != len(selected):
            message = "偏好候选已变化，未启用；请根据最新候选重新申请。"
            bus.publish(ctx.shopping_session_id, "tool.result", {"tool": "activate_preferences_tool", "error": message})
            return ToolChunk(content=[TextBlock(text="[error] "+message)], state=ToolResultState.ERROR)
        ShoppingContext.activate_preferences(
            [(p.memory_id, p.kind, p.statement, p.version) for p in selected],
            material_exclusion_tags(selected),
        )
        payload = {"activated": [{"memory_id": p.memory_id, "version": p.version,
            "kind": p.kind, "statement": p.statement} for p in selected], "scope": "current_run_only"}
        bus.publish(ctx.shopping_session_id, "tool.result", {"tool": "activate_preferences_tool", **payload})
        return ToolChunk(content=[TextBlock(text=render_preference_hint(selected)+"\n"+json.dumps(payload,ensure_ascii=False))],
                         state=ToolResultState.SUCCESS)
    return activate_preferences_tool
