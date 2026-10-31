# QQ 资料上下文

面向 AstrBot 4.29.1 的 OneBot v11（aiocqhttp）插件。目标协议端为 SnowLuma v1.14.21，尚未完成该协议端的实机验证，不能保证其返回所有字段。

## 功能

- LLM 请求前自动附带当前发言者资料和消息中被 @ 用户的资料。
- 提供 `get_qq_user_info` 工具，让支持工具调用的模型按 QQ 号查询。
- `/qqinfo` 查看自己的资料；`/qqinfo @某人` 或 `/qqinfo QQ号` 查询当前群的成员。
- 性别、年龄、昵称、群名片、群身份等以接口返回及插件配置为准；未知值不猜测。
- 内存缓存、查询超时、@ 数量限制；失败时不阻断正常聊天。

## 安装

将整个插件目录放进 AstrBot 的 `data/plugins/astrbot_plugin_get_qq_status`，在 WebUI 重载插件或重启 AstrBot。也可将插件源文件压成 ZIP 后从 WebUI 上传安装。无需第三方依赖。

确保 SnowLuma 在 AstrBot 中使用 **OneBot v11 / aiocqhttp** 适配器。打开插件配置，检查自动注入及字段开关；在当前人格/会话的工具选择中启用 `get_qq_user_info`，并使用支持工具调用的模型。

## 性别和年龄诊断

重载插件后发送 `/qqdiag`。只查询发言者本人，忽略 @，不使用插件缓存；分别展示两个接口的调用状态及 sex/age 是否存在、原始标量值和类型，不展示其他资料，也不注册为 LLM 工具。私聊只检查 get_stranger_info；要比较两个接口请在群内执行，注意结果会对群成员可见。

`present: false` 表示字段缺失，`value: null` 表示接口返回空值，`unknown` 表示返回未知。失败与超时单独显示，不误判为资料未设置。请勿粘贴令牌或其他完整原始资料。

## 验收

1. 私聊发送 `/qqinfo`，确认实际可获取的资料。
2. 群聊发送 `/qqinfo @某人`，检查群名片、群身份等。
3. @ 机器人正常聊天并问“我的 QQ 资料性别是什么”；再 @ 一位群友询问其 QQ 资料。应回答接口值或未知，不得猜测。
4. 请求模型查询本群某 QQ 号，检查工具调用记录。
5. 如不成功，先检查适配器和 SnowLuma 的 `get_stranger_info`、`get_group_member_info` 接口；性别/年龄缺失不等于插件加载失败。

## 边界与隐私

资料会随聊天上下文发送给所配置的模型服务。请告知群成员并遵守群规则，只开启必要字段；不需要时关闭插件。缓存仅保存在进程内，不写入本地资料数据库，但模型服务和 AstrBot 自身的历史/日志策略仍可能保留发送内容。

QQ 资料性别和年龄是账号资料，不代表真实身份。昵称、名片、头衔等属于不可信数据，插件会将其标记为数据而不是指令；这不能替代模型自身的提示注入防护。

主动查询限制为私聊本人或当前群中能经接口确认的成员，不提供跨群/任意陌生人枚举。SnowLuma 的接口权限和返回字段决定最终能力。查询资料不需要管理员权限，不涉及修改群资料、禁言等管理操作。

## 开发参考

- [AstrBot 工具开发文档](https://docs.astrbot.app/dev/star/guides/ai.html)
- [AstrBot v4.29.1 OneBot 事件源码](https://github.com/AstrBotDevs/AstrBot/blob/v4.29.1/astrbot/core/platform/sources/aiocqhttp/aiocqhttp_message_event.py)

已核对该版本使用 `event.bot.call_action` 调用 OneBot，并通过 `self_id` 路由机器人账号。仍需实际 SnowLuma 联调。

## 开发测试

`python -m unittest discover -s tests -v`

自动测试使用模拟 AstrBot 与 OneBot，不等同于 SnowLuma 或真实模型的端到端验证。
