import time
import textwrap
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, At



@register("anti_repeat", "灵汐", "防重复指令拦截器", "1.0.2")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.history = {}
        self.cooldown_seconds = 3.0

    # 指令部分
    @filter.command("lxhelp", alias={"拦截帮助"})
    async def lxhelp(self, event: AstrMessageEvent):
        help_message = textwrap.dedent(f"""
            【灵汐指令拦截帮助】

            [介绍]
            当同一用户在 {self.cooldown_seconds}s 内发送两次相同内容，将自动拦截后续指令。

            [指令列表]
            1. #冷却设置 <秒数>
            2. #拦截帮助
            """).strip()
        yield event.plain_result(help_message)


    @filter.command("set_cooldown", alias={"冷却设置"})
    @filter.permission_type(PermissionType.ADMIN)
    async def set_cd(self, event: AstrMessageEvent, seconds: str):
        #'''设置拦截冷却时间 (仅管理员)'''
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

    # === 事件监听部分 (绝对不能用 yield) ===
    # 优先级 priority=0 通常是默认，设置高一点(例如10)可以让它在其他插件之前运行
    @filter.event_message_type(EventMessageType.ALL, priority=10)
    async def intercept_repeats(self, event: AstrMessageEvent):
        # 1. 基础检查
        content = event.message_str
        if not content:
            return

        # 白名单：帮助指令不拦截
        if "lx_helps" in content:
            return

        user_id = event.get_sender_id()
        key = f"{user_id}:{content}"
        current_time = time.time()

        # 2. 检查冷却
        if key in self.history:
            last_time = self.history[key]
            if current_time - last_time < self.cooldown_seconds:
                # === 触发拦截 ===

                # 注意：事件监听器不能 yield，必须用 send_message 主动发送
                # 构建消息链
                umo = event.unified_msg_origin
                message_chain = MessageChain().message("核心逻辑混乱，不要再发啦！")

                # 发送警告
                async def send_warn(numa: int):
                    if numa == 1:
                        await self.context.send_message(
                            event.unified_msg_origin,
                            message_chain
                        )
                        numa = numa -1
                    elif numa == 2:
                        pass
                    else:
                        print("程序出现异常，运行可能失败")
                        pass

                # 核心：停止事件传播，阻止其他插件处理这条消息
                event.stop_event()
                return

        # 3. 更新记录
        self.history[key] = current_time

        # 简单清理
        if len(self.history) > 1000:
            self.cleanup_history()

    def cleanup_history(self):
        current_time = time.time()
        self.history = {
            k: v for k, v in self.history.items()
            if current_time - v < self.cooldown_seconds
        }
