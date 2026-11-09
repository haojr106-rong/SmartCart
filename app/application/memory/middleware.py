"""遵循 AgentScope 2.x MiddlewareBase 的偏好候选召回接入。

仅用户明确通过页面或记忆工具写入，不将助手输出自动沉淀成买家事实。
后端只需实现 list_by_buyer/select，后续可替换为 Mem0/ReMe 适配器。
"""
from agentscope.middleware import MiddlewareBase
from agentscope.message import UserMsg
from app.infrastructure.context import ShoppingContext
import re

from app.application.memory.preference_selector import render_preference_candidates


_SHOPPING_INTENT = re.compile(
    r"推荐|帮我找|给我找|想买|要买|购买|下单|候选|商品清单|有哪些|有没有|"
    r"给我看看|\d+(?:\.\d+)?\s*(?:元|块|美元|美金)|以内|以下|不超过|"
    r"选[一二三四五六七八九十两\d]+(?:个|件|款)|挑[一二三四五六七八九十两\d]+(?:个|件|款)"
)
_MEMORY_MANAGEMENT = re.compile(r"记住|长期偏好|删除.*偏好|修改.*偏好|不再喜欢|以后不用|改成喜欢")


def should_offer_preference_candidates(query: str) -> bool:
    """只为具体购物或记忆管理提供候选；纯商品知识问题保持无偏好。"""
    return bool(_SHOPPING_INTENT.search(query) or _MEMORY_MANAGEMENT.search(query))

class BuyerMemoryMiddleware(MiddlewareBase):
    def __init__(self,store,top_k=5):self.store=store;self.top_k=top_k

    async def on_reply(self,agent,input_kwargs,next_handler):
        ctx=ShoppingContext.current()
        if ctx is None:raise ValueError('长期记忆缺少买家上下文')
        inputs=input_kwargs.get('inputs') or []
        inputs=inputs if isinstance(inputs,list) else [inputs]
        user=next((m for m in reversed(inputs) if getattr(m,'name',None)==ctx.buyer_id),None)
        if user is not None:
            query=user.get_text_content()
            inputs=[m for m in inputs if getattr(m,'name',None) not in {'memory_hint','preference_candidates'}]
            if not should_offer_preference_candidates(query):
                input_kwargs={**input_kwargs,'inputs':inputs}
                async for event in next_handler(**input_kwargs):yield event
                return
            preferences=await self.store.list_by_buyer(ctx.buyer_id)
            selected=await self.store.select(preferences,query,self.top_k)
            # 候选仅供申请本轮授权，不能作为已经生效的 memory_hint 注入。
            if selected:
                inputs.insert(0,UserMsg('preference_candidates',render_preference_candidates(selected)))
            input_kwargs={**input_kwargs,'inputs':inputs}
        async for event in next_handler(**input_kwargs):yield event
