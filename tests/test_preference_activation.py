import asyncio

from agentscope.message import ToolCallBlock, ToolCallState
from agentscope.permission import PermissionBehavior

from app.application.agents.tool_confirmation import MemoryPermissionMiddleware
from app.application.tools.activate_preferences_tool import build_activate_preferences_tool
from app.domain.buyer.preference import BuyerPreference
from app.infrastructure.context import ShoppingContext, ShoppingContextSnapshot
from app.infrastructure.eventbus import TradeEventBus


class Store:
    def __init__(self, preferences=()):
        self.preferences=list(preferences)
    async def list_by_buyer(self,buyer_id):
        return [p for p in self.preferences if p.buyer_id==buyer_id]


async def test_activation_requires_confirmation_and_only_affects_current_run():
    store=Store([BuyerPreference('buyer','like','喜欢轻便',memory_id='memory-1',version=1)])
    preference=(await store.list_by_buyer('buyer'))[0]
    middleware=MemoryPermissionMiddleware(store)
    call=ToolCallBlock(id='activate',name='activate_preferences_tool',input='{}')
    values={'memory_ids':[preference.memory_id], 'expected_versions':[preference.version],
            'statements':[preference.statement]}
    token=ShoppingContext.set(ShoppingContextSnapshot('session','buyer','zh-CN','CNY'))
    try:
        async def handler(**kwargs):
            raise AssertionError('未确认前不能放行')
        decision=await asyncio.wait_for(middleware.on_check_permission(None,{'tool_call':call,'tool_input':values},handler),2)
        assert decision.behavior==PermissionBehavior.ASK
        call.state=ToolCallState.ALLOWED
        tool=build_activate_preferences_tool(store,TradeEventBus())
        result=await asyncio.wait_for(tool(**values),2)
        assert '喜欢轻便' in result.content[0].text
        assert ShoppingContext.current_activated_preferences()[0][2]=='喜欢轻便'
    finally:
        ShoppingContext.reset(token)


async def test_activation_rejects_stale_candidate():
    store=Store()
    middleware=MemoryPermissionMiddleware(store)
    call=ToolCallBlock(id='activate',name='activate_preferences_tool',input='{}')
    token=ShoppingContext.set(ShoppingContextSnapshot('session','buyer','zh-CN','CNY'))
    try:
        async def handler(**kwargs):
            raise AssertionError('过期候选不能放行')
        decision=await asyncio.wait_for(middleware.on_check_permission(None,{'tool_call':call,'tool_input':{
            'memory_ids':['missing'],'expected_versions':[1],'statements':['喜欢轻便']}},handler),2)
        assert decision.behavior==PermissionBehavior.DENY
    finally:
        ShoppingContext.reset(token)

