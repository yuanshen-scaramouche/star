import time
import json
import os
import textwrap
from astrbot.core.utils.astrbot_path import get_astrbot_data_path
from astrbot.api.event import filter, AstrMessageEvent, MessageChain
from astrbot.api.event.filter import EventMessageType, PermissionType
from astrbot.api.star import Context, Star, register


@register("anti_repeat", "灵汐", "防重复指令拦截器", "1.0.5")
class AntiRepeatPlugin(Star):
    def __init__(self, context: Context, config_file="config.json"):
        super().__init__(context)
        # 记录结构: key -> {'time': float, 'warned': bool}
        self.history = {}

        # 默认配置值
        self.cooldown_seconds = 3.0
        self.cmd = ['/']  # 默认唤醒前缀
        self.WarnMessage = "核心逻辑混乱，不要再发啦！"  # 警告消息
        self.GJC = []  # 关键词列表
        self.enable_keyword_check = False  # 是否启用关键词检查
        self.enable_warn_word_check = True     #是否启用言语警告
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
                    self.GJC = data.get("gjc", self.GJC)
                    self.enable_keyword_check = data.get("enable_keyword_check", self.enable_keyword_check)
                    self.enable_warn_word_check = data.get("enable_warn_word_check", self.enable_warn_word_check)
                    print(
                        f"成功读取配置: CD={self.cooldown_seconds}s, 前缀={self.cmd}, 关键词检查={self.enable_keyword_check}")

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
                "warn_message": self.WarnMessage,
                "gjc": self.GJC,
                "enable_keyword_check": self.enable_keyword_check
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
            关键词检查状态: {'开启' if self.enable_keyword_check else '关闭'}

            [指令]
            注意：除帮助指令外需要添加lx为主指令。
            当前警告语句：{self.WarnMessage}

            1. lxhelp 或 拦截帮助 -> 获得拦截插件帮助信息
            2. set_cooldown 或 冷却设置 -> 调整冷却时间 (当前: {self.cooldown_seconds}s)
            3. 传入指令前缀 / 删除指令前缀 -> 管理触发拦截的指令头
            4. 设置警告 -> 设置触发拦截时的回复内容
            5. 设置关键词 -> 设置关键词（多个用逗号分隔）
            6. 添加关键词 -> 添加单个关键词
            7. 删除关键词 -> 删除单个关键词
            8. 开关关键词检查 -> 启用/禁用关键词检查功能
            9. 查看关键词列表 -> 显示当前关键词列表
            10. 开关警告词 -> 开关用户多次发送唤醒机器人时是否发送警告词
            
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

    # 开关发送警告
    @lx.command('开关警告词发送', alias={'开关警告词'})
    @filter.permission_type(PermissionType.ADMIN)
    async def toggle_warn_word_check(self, event: AstrMessageEvent):
        self.enable_warn_word_check = not self.enable_warn_word_check
        self.save_config()
        status = "开启" if self.enable_warn_word_check else "关闭"
        yield event.plain_result(f'警告词功能已{status}')

    # 设置关键词（覆盖）
    @lx.command('设置关键词')
    @filter.permission_type(PermissionType.ADMIN)
    async def set_keywords(self, event: AstrMessageEvent, keywords: str):
        # 按空格或逗号分割关键词
        self.GJC = [k.strip() for k in keywords.replace('，', ',').split(',') if k.strip()]
        self.save_config()
        yield event.plain_result(f'已设置关键词：{self.GJC}')

    # 添加关键词而不是覆盖
    @lx.command('添加关键词')
    @filter.permission_type(PermissionType.ADMIN)
    async def add_keyword(self, event: AstrMessageEvent, keyword: str):
        if keyword not in self.GJC:
            self.GJC.append(keyword)
            self.save_config()
            yield event.plain_result(f'已添加关键词：{keyword}，当前列表：{self.GJC}')
        else:
            yield event.plain_result(f'关键词 {keyword} 已存在')

    # 删除关键词
    @lx.command('删除关键词', alias={'关键词删除'})
    @filter.permission_type(PermissionType.ADMIN)
    async def del_keyword(self, event: AstrMessageEvent, keyword: str):
        if keyword in self.GJC:
            self.GJC.remove(keyword)
            self.save_config()  # 保存配置
            yield event.plain_result(f'关键词删除成功！当前列表：{self.GJC}')
        else:
            yield event.plain_result(f'关键词 {keyword} 不在列表中。')

    # 开关关键词检查功能
    @lx.command('开关关键词检查', alias={'切换关键词检查'})
    @filter.permission_type(PermissionType.ADMIN)
    async def toggle_keyword_check(self, event: AstrMessageEvent):
        self.enable_keyword_check = not self.enable_keyword_check
        self.save_config()
        status = "开启" if self.enable_keyword_check else "关闭"
        yield event.plain_result(f'关键词检查功能已{status}')

    # 查看关键词列表
    @lx.command('查看关键词列表', alias={'显示关键词', '关键词列表'})
    @filter.permission_type(PermissionType.ADMIN)
    async def show_keywords(self, event: AstrMessageEvent):
        if self.GJC:
            keywords_str = "\n".join([f"{i + 1}. {keyword}" for i, keyword in enumerate(self.GJC)])
            yield event.plain_result(
                f"当前关键词列表：\n{keywords_str}\n\n关键词检查功能：{'开启' if self.enable_keyword_check else '关闭'}")
        else:
            yield event.plain_result("当前没有设置关键词。")

    # === 事件监听部分 ===
    @filter.event_message_type(EventMessageType.ALL, priority=10)
    async def intercept_repeats(self, event: AstrMessageEvent):
        # 1. 基础检查
        content = event.message_str
        if not content:
            return

        # 2. 判断是否需要检查
        need_check = False

        # 检查是否被@或包含唤醒前缀
        if event.is_at_or_wake_command:
            need_check = True
        # 检查是否包含关键词（仅在启用关键词检查时）
        elif self.enable_keyword_check and self.GJC and any(keyword in content for keyword in self.GJC):
            need_check = True

        if not need_check:
            return

        # 3. 创建唯一标识
        user_id = event.get_sender_id()
        key = f"{user_id}:{content}"
        current_time = time.time()

        # 4. 检查冷却
        if key in self.history:
            record = self.history[key]
            last_time = record['time']
            has_warned = record['warned']

            if current_time - last_time < self.cooldown_seconds:
                # === 触发拦截 ===
                # 只有在还没警告过的情况下，才发送警告
                if not has_warned:
                    if not self.enable_warn_word_check:
                        return
                    message_chain = MessageChain().message(self.WarnMessage)
                    await self.context.send_message(
                        event.unified_msg_origin,
                        message_chain
                    )
                    # 标记该记录为"已警告"
                    self.history[key]['warned'] = True

                # 更新时间防止无限刷（可选，延长冷却）
                self.history[key]['time'] = current_time

                # 核心：停止事件传播
                event.stop_event()
                return

        # 5. 更新/新建记录 (重置 warned 状态)
        self.history[key] = {
            'time': current_time,
            'warned': False
        }

        # 6. 简单清理
        if len(self.history) > 1000:
            self.cleanup_history()

    def cleanup_history(self):
        current_time = time.time()
        # 字典推导式清理过期数据
        self.history = {
            k: v for k, v in self.history.items()
            if current_time - v['time'] < self.cooldown_seconds * 2  # 保留稍长时间的历史记录
        }