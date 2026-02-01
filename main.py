import time
import textwrap
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register


@register("anti_repeat", "灵汐", "防重复指令拦截器", "1.0.3")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        # 记录结构: key -> {'time': float, 'warned': bool}
        self.history = {}
        self.cooldown_seconds = 3.0

    # ... (lxhelp 和 set_cd 部分保持不变) ...
    @filter.command("lxhelp", alias={"拦截帮助"})
    async def lxhelp(self, event: AstrMessageEvent):
        help_message = textwrap.dedent(f"""
            【灵汐指令拦截帮助】
            [介绍]
            当同一用户在 {self.cooldown_seconds}s 内发送两次相同内容，将自动拦截后续指令。
            """).strip()
        yield event.plain_result(help_message)

    @filter.command("set_cooldown", alias={"冷却设置"})
    @filter.permission_type(PermissionType.ADMIN)
    async def set_cd(self, event: AstrMessageEvent, seconds: str):
        try:
            new_time = float(seconds)
            if new_time < 0:
                yield event.plain_result("冷却时间不能为负数。")
                return
            self.cooldown_seconds = new_time
            self.history.clear()
            yield event.plain_result(f"冷却时间已更新为: {self.cooldown_seconds} 秒")
        except ValueError:
            yield event.plain_result("格式错误，请输入数字。")

    # === 事件监听部分 ===
    @filter.event_message_type(EventMessageType.ALL, priority=10)
    async def intercept_repeats(self, event: AstrMessageEvent):
        # 1. 基础检查
        content = event.message_str
        if not content:
            return

        # 白名单：帮助指令不拦截
        if "lxhelp" in content or "拦截帮助" in content:
            return

        user_id = event.get_sender_id()
        key = f"{user_id}:{content}"
        current_time = time.time()

        # 2. 检查冷却
        if key in self.history:
            record = self.history[key]
            last_time = record['time']
            has_warned = record['warned']

            if current_time - last_time < self.cooldown_seconds:
                # === 触发拦截 ===

                # 只有在还没警告过的情况下，才发送警告
                if not has_warned:
                    message_chain = MessageChain().message("核心逻辑混乱，不要再发啦！")
                    await self.context.send_message(
                        event.unified_msg_origin,
                        message_chain
                    )
                    # 标记该记录为“已警告”
                    self.history[key]['warned'] = True
                    # 更新时间，延长冷却（可选，看你是否希望刷屏持续刷新冷却时间）
                    self.history[key]['time'] = current_time

                    # 核心：停止事件传播
                event.stop_event()
                return

        # 3. 更新/新建记录 (重置 warned 状态)
        self.history[key] = {
            'time': current_time,
            'warned': False
        }

        # 简单清理
        if len(self.history) > 1000:
            self.cleanup_history()

    def cleanup_history(self):
        current_time = time.time()
        # 字典推导式清理过期数据
        self.history = {
            k: v for k, v in self.history.items()
            if current_time - v['time'] < self.cooldown_seconds
        }
