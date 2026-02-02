import time
import json
import os
import textwrap
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register


@register("anti_repeat", "灵汐", "防重复指令拦截器", "1.0.4")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context, config_file="config.json"):
        super().__init__(context)
        # 记录结构: key -> {'time': float, 'warned': bool}
        self.history = {}

        # 默认配置值
        self.cooldown_seconds = 3.0
        self.cmd = ['/']  # 默认唤醒前缀
        self.WarnMessage = "核心逻辑混乱，不要再发啦！"  # 警告消息

        self.config_file = config_file

        # 加载配置
        self.load_config()

    def load_config(self):
        """启动时从文件读取配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 兼容旧版本：如果文件里只是个列表，说明是旧配置
                if isinstance(data, list):
                    self.cmd = data
                    print("检测到旧版配置，已加载指令前缀，将自动迁移到新格式。")
                    self.save_config()  # 立即保存为新格式
                elif isinstance(data, dict):
                    # 读取新版配置，如果不存在则使用默认值
                    self.cmd = data.get("cmd", self.cmd)
                    self.cooldown_seconds = data.get("cooldown_seconds", self.cooldown_seconds)
                    self.WarnMessage = data.get("warn_message", self.WarnMessage)
                    print(f"成功读取配置: CD={self.cooldown_seconds}s, 前缀={self.cmd}")

            except Exception as e:
                print(f"读取失败，使用默认配置。错误: {e}")
        else:
            print("配置文件不存在，将使用初始配置并创建文件。")
            self.save_config()

    def save_config(self):
        """将当前的所有配置保存到文件"""
        try:
            data = {
                "cmd": self.cmd,
                "cooldown_seconds": self.cooldown_seconds,
                "warn_message": self.WarnMessage
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # indent=4 可以让生成的 json 文件带缩进，方便阅读
                json.dump(data, f, ensure_ascii=False, indent=4)
            print("配置已保存到本地。")
        except Exception as e:
            print(f"保存失败: {e}")

    @filter.command_group('lx')
    def lx(self):
        pass

    @filter.command("lxhelp", alias={"拦截帮助"})
    async def lxhelp(self, event: AstrMessageEvent):
        help_message = textwrap.dedent(f"""
            【灵汐指令拦截帮助】
            [介绍]
            当同一用户在 {self.cooldown_seconds}s 内发送两次相同内容，将自动拦截后续指令。

            [指令]
            注意：除帮助指令外需要添加lx为主指令。
            当前警告语句：{self.WarnMessage}

            1. lxhelp 或 拦截帮助 -> 获得拦截插件帮助信息
            2. set_cooldown 或 冷却设置 -> 调整冷却时间 (当前: {self.cooldown_seconds}s)
            3. 传入指令前缀 / 删除指令前缀 -> 管理触发拦截的指令头(本指令已废弃，无需使用此指令)
            4. 设置警告 -> 设置触发拦截时的回复内容

            """).strip()
        yield event.plain_result(help_message)

    @lx.command("set_cooldown", alias={"冷却设置"})
    @filter.permission_type(PermissionType.ADMIN)
    async def set_cd(self, event: AstrMessageEvent, seconds: str):
        try:
            new_time = float(seconds)
            if new_time < 0:
                yield event.plain_result("冷却时间不能为负数。")
                return

            self.cooldown_seconds = new_time
            self.history.clear()  # 清空历史记录以应用新时间
            self.save_config()  # 保存配置

            yield event.plain_result(f"冷却时间已更新为: {self.cooldown_seconds} 秒并已保存。")
        except ValueError:
            yield event.plain_result("格式错误，请输入数字。")

    # 传入唤醒指令
    @lx.command('传入指令前缀', alias={'指令前缀', '指令前缀传入'})
    @filter.permission_type(PermissionType.ADMIN)
    async def add_cmd_func(self, event: AstrMessageEvent, cm: str):
        if cm not in self.cmd:
            self.cmd.append(cm)
            self.save_config()  # 保存配置
            yield event.plain_result(f'唤醒前缀传入成功！当前列表：{self.cmd}')
        else:
            yield event.plain_result(f'前缀 {cm} 已存在。')

    # 删除唤醒指令
    @lx.command('删除指令前缀', alias={'指令前缀删除'})
    @filter.permission_type(PermissionType.ADMIN)
    async def del_cmd_func(self, event: AstrMessageEvent, cm: str):
        if cm in self.cmd:
            self.cmd.remove(cm)
            self.save_config()  # 保存配置
            yield event.plain_result(f'唤醒前缀删除成功！当前列表：{self.cmd}')
        else:
            yield event.plain_result(f'前缀 {cm} 不在列表中。')

    # 设置警告语句
    @lx.command('设置警告')
    @filter.permission_type(PermissionType.ADMIN)
    async def set_warnmessage(self, event: AstrMessageEvent, wm: str):
        self.WarnMessage = wm
        self.save_config()  # 保存配置
        yield event.plain_result(f'警告语句已更新并保存：{self.WarnMessage}')

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

        if not event.is_at_or_wake_command: return

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
                    message_chain = MessageChain().message(self.WarnMessage)
                    await self.context.send_message(
                        event.unified_msg_origin,
                        message_chain
                    )
                    # 标记该记录为“已警告”
                    self.history[key]['warned'] = True

                # 无论是否警告过，只要在冷却内且触发了拦截，都更新时间防止无限刷
                # 如果你不希望刷屏延长冷却，可以注释掉下面这行
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


"""标题：@悲伤玉米糊ovo 我恨自己是个姐姐控。一有事就喊姐姐，闹脾气也要在姐姐面前装的可爱，跟姐姐说话一定是柔声细语，受一点伤我都要委屈找姐姐，天天围着姐姐转，窝在姐姐怀里撒娇。想姐姐等姐姐爱姐姐，姐姐好美，吃饭想姐姐，睡觉想姐姐，洗澡想姐姐，干什么都想姐姐，太喜欢姐姐了，眼泪流干也要喜欢
作者：moyidian(uid:dym3aq3w8z31)
发布时间：2026-01-18
原始链接：https://www.douyin.com/note/7596716170209329262"""