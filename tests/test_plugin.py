"""Offline contract tests; no AstrBot installation or QQ account required."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


def install_stubs():
    names = ['astrbot', 'astrbot.api', 'astrbot.api.event', 'astrbot.api.message_components',
             'astrbot.api.provider', 'astrbot.api.star']
    for name in names:
        sys.modules[name] = types.ModuleType(name)
    class Star:
        def __init__(self, context): pass
    class At:
        def __init__(self, qq): self.qq = qq
    def deco(*args, **kwargs):
        return lambda func: func
    sys.modules['astrbot.api'].AstrBotConfig = dict
    sys.modules['astrbot.api.event'].AstrMessageEvent = object
    sys.modules['astrbot.api.event'].filter = types.SimpleNamespace(
        on_llm_request=deco, llm_tool=deco, command=deco)
    sys.modules['astrbot.api.message_components'].At = At
    sys.modules['astrbot.api.provider'].ProviderRequest = object
    mod = sys.modules['astrbot.api.star']
    mod.Context, mod.Star, mod.register = object, Star, deco
    return At

At = install_stubs()
spec = importlib.util.spec_from_file_location('qq_plugin_test_target', Path(__file__).resolve().parents[1] / 'main.py')
plugin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plugin)

class Bot:
    def __init__(self):
        self.calls = []
        self.fail = set()
    async def call_action(self, action, **kw):
        self.calls.append((action, kw))
        if action in self.fail: raise RuntimeError('offline')
        data = {'user_id': kw['user_id'], 'nickname': '测试昵称', 'sex': 'female', 'age': 20}
        if action == 'get_group_member_info':
            data.update(group_id=kw['group_id'], card='群名片', role='admin', title='头衔', level='10')
        return data

class Event:
    def __init__(self, group='', ats=(), account='999'):
        self.bot = Bot()
        self.message_obj = types.SimpleNamespace(self_id=account)
        self.group, self.ats = group, [At(x) for x in ats]
    def get_platform_name(self): return 'aiocqhttp'
    def get_sender_id(self): return '12345'
    def get_group_id(self): return self.group
    def get_messages(self): return self.ats
    def plain_result(self, text): return text

class Tests(unittest.IsolatedAsyncioTestCase):
    def make_plugin(self, **config):
        return plugin.QQStatusPlugin(None, config)
    async def test_self_lookup_and_routing(self):
        p, e = self.make_plugin(), Event()
        value = await p._lookup(e, '12345')
        self.assertEqual(value['qq_profile_sex'], 'female')
        self.assertEqual(e.bot.calls[0][1]['self_id'], '999')
    async def test_private_stranger_denied(self):
        p, e = self.make_plugin(), Event()
        self.assertIsInstance(await p._lookup(e, '67890'), str)
        self.assertEqual(e.bot.calls, [])
    async def test_invalid_ids(self):
        p, e = self.make_plugin(), Event()
        for uid in ('all', '0', '-1', '１２３', '123 abc'):
            self.assertIsInstance(await p._lookup(e, uid), str)
        self.assertEqual(e.bot.calls, [])
    async def test_member_authorization_failure(self):
        p, e = self.make_plugin(), Event(group='444')
        e.bot.fail.add('get_group_member_info')
        self.assertIsInstance(await p._lookup(e, '67890'), str)
        self.assertNotIn('get_stranger_info', [a for a, _ in e.bot.calls])
    async def test_cache(self):
        p, e = self.make_plugin(), Event()
        await p._lookup(e, '12345')
        calls = len(e.bot.calls)
        await p._lookup(e, '12345')
        self.assertEqual(len(e.bot.calls), calls)
        e.message_obj.self_id = '888'
        await p._lookup(e, '12345')
        self.assertGreater(len(e.bot.calls), calls)
    async def test_disabled(self):
        p, e = self.make_plugin(enabled=False), Event()
        self.assertIsInstance(await p._lookup(e, '12345'), str)
        self.assertFalse(e.bot.calls)
    async def test_inject_and_at_limit(self):
        p, e = self.make_plugin(max_at=1), Event(group='444', ats=['67890', '77777', 'all'])
        req = types.SimpleNamespace(system_prompt='原始人设', extra_user_content_parts=[])
        await p.inject_qq_info(e, req)
        content = req.system_prompt + json.dumps(req.extra_user_content_parts)
        self.assertIn('12345', content)
        self.assertIn('67890', content)
        self.assertNotIn('77777', content)
        self.assertTrue(req.system_prompt.startswith('原始人设'))
    async def test_failure_does_not_block_hook(self):
        p, e = self.make_plugin(), Event()
        e.bot.fail.update(['get_stranger_info', 'get_group_member_info'])
        req = types.SimpleNamespace(system_prompt='original', extra_user_content_parts=[])
        await p.inject_qq_info(e, req)
        self.assertEqual(req.system_prompt, 'original')
    async def test_command_and_tool(self):
        p, e = self.make_plugin(), Event()
        self.assertIn('12345', await p.get_qq_user_info(e, '12345'))
        replies = [r async for r in p.qqinfo(e)]
        self.assertEqual(len(replies), 1)
        self.assertIn('12345', replies[0])
    async def test_cache_bound(self):
        p, e = self.make_plugin(cache_size=1), Event(group='444')
        await p._lookup(e, '12345')
        await p._lookup(e, '67890')
        self.assertLessEqual(len(p._cache), 1)
    async def test_group_fields(self):
        p, e = self.make_plugin(fields=['nickname', 'sex', 'age', 'card', 'role']), Event(group='444')
        value = await p._lookup(e, '12345')
        self.assertEqual(value['card'], '群名片')
        self.assertEqual(value['group_role'], 'admin')
    async def test_member_fallback(self):
        p, e = self.make_plugin(), Event(group='444')
        e.bot.fail.add('get_stranger_info')
        self.assertIsInstance(await p._lookup(e, '67890'), dict)
    async def test_envelope(self):
        p, e = self.make_plugin(), Event()
        original = e.bot.call_action
        async def wrapped(action, **kw):
            return {'status': 'ok', 'retcode': 0, 'data': await original(action, **kw)}
        e.bot.call_action = wrapped
        self.assertIsInstance(await p._lookup(e, '12345'), dict)
    async def test_unknown_fields_not_invented(self):
        p = self.make_plugin()
        value = p._select('12345', {'user_id': 12345, 'age': None, 'sex': None})
        self.assertNotIn('qq_profile_sex', value)
        self.assertNotIn('qq_profile_age', value)

if __name__ == '__main__': unittest.main()
