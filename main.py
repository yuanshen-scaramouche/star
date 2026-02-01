import time
import json
import re
import os
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
import textwrap
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register


@register("anti_repeat", "灵汐", "防重复指令拦截器", "1.0.3")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context, config_file="config.json"):
        super().__init__(context)
        # 记录结构: key -> {'time': float, 'warned': bool}
        self.history = {}
        self.cooldown_seconds = 3.0
        self.config_file = config_file
        self.cmd = ['/']  #默认唤醒前缀
        self.load_cmd()
        self.WarnMessage = "核心逻辑混乱，不要再发啦！"  #警告消息

    def load_cmd(self):
        """启动时从文件读取数组"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.cmd = json.load(f)
                print(f"成功读取配置: {self.cmd}")
            except Exception as e:
                print(f"读取失败，使用默认配置。错误: {e}")
        else:
            print("配置文件不存在，将使用初始配置并创建文件。")
            self.save_cmd()

    def save_cmd(self):
        """将当前的 self.cmd 保存到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # indent=4 可以让生成的 json 文件带缩进，方便阅读
                json.dump(self.cmd, f, ensure_ascii=False, indent=4)
            print("配置已保存到本地。")
        except Exception as e:
            print(f"保存失败: {e}")

    def add_prefix(self, new_prefix):
        """添加前缀并立即保存"""
        if new_prefix not in self.cmd:
            self.cmd.append(new_prefix)
            self.save_cmd()

    @filter.command_group('lx')
    def lx(self):
        pass

    # ... (lxhelp 和 set_cd 部分保持不变) ...
    @filter.command("lxhelp", alias={"拦截帮助"})
    async def lxhelp(self, event: AstrMessageEvent):
        help_message = textwrap.dedent(f"""
            【灵汐指令拦截帮助】
            [介绍]
            当同一用户在 {self.cooldown_seconds}s 内发送两次相同内容，将自动拦截后续指令。
            
            [指令]
            注意：除帮助指令外需要添加lx为主指令，如 lx 设置警告 | 正确, 设置警告 | 无法识别。 
            1. lxhelp 或 拦截帮助 -> 获得拦截插件帮助信息
            2. set_cooldown 或 冷却设置 -> 调整冷却时间为 x.x 浮点数
            3. 传入指令前缀 或 指令前缀 或 指令前缀传入 -> 传入指令前缀
            4. 设置警告 -> 设置多次发送消息给机器人时的提示信息
            
            
            ###重要提醒：使用前必须使用 传入指令前缀 传入指令前缀!传入前缀不会改变配置文件内容，仅与插件内部审核进行对照！
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
            self.history.clear()
            yield event.plain_result(f"冷却时间已更新为: {self.cooldown_seconds} 秒")
        except ValueError:
            yield event.plain_result("格式错误，请输入数字。")

    #传入唤醒指令
    @lx.command('传入指令前缀', alias={'指令前缀', '指令前缀传入'} )
    @filter.permission_type(PermissionType.ADMIN)
    async def set_cmd(self, event: AstrMessageEvent, cm: str):
        self.cmd.append(cm)
        self.save_cmd()
        self.load_cmd()
        yield event.plain_result(f'唤醒前缀传入成功！传入前缀为：{self.cmd}')

    #删除唤醒指令
    @lx.command('删除指令前缀', alias={'指令前缀删除'} )
    @filter.permission_type(PermissionType.ADMIN)
    async def set_cmd(self, event: AstrMessageEvent, cm: str):
        self.cmd.remove(cm)
        self.save_cmd()
        self.load_cmd()
        yield event.plain_result(f'唤醒前缀删除成功！删除前缀为：{self.cmd}')

    #设置警告语句
    @lx.command('设置警告')
    @filter.permission_type(PermissionType.ADMIN)
    async def set_warnmessage(self, event: AstrMessageEvent, wm: str):
        self.WarnMessage = wm
        yield  event.plain_result(f'警告语句已改为：{self.WarnMessage}')

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

        # 检查是否包含唤醒词
        if not content.startswith(tuple(self.cmd)):
            return  # 只要开头不是这些符号中的任何一个，直接退出

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
                    wms = self.WarnMessage
                    message_chain = MessageChain().message(wms)
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


"""标题：@悲伤玉米糊ovo 我恨自己是个姐姐控。一有事就喊姐姐，闹脾气也要在姐姐面前装的可爱，跟姐姐说话一定是柔声细语，受一点伤我都要委屈找姐姐，天天围着姐姐转，窝在姐姐怀里撒娇。想姐姐等姐姐爱姐姐，姐姐好美，吃饭想姐姐，睡觉想姐姐，洗澡想姐姐，干什么都想姐姐，太喜欢姐姐了，眼泪流干也要喜欢
作者：moyidian(uid:dym3aq3w8z31)
发布时间：2026-01-18
原始链接：https://www.douyin.com/note/7596716170209329262"""
