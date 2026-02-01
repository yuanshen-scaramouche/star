# Anti-Repeat (灵汐防刷屏插件)

一款为 AstrBot 打造的指令冷却与防重复拦截插件。有效防止用户刷屏，保护机器人响应资源，让指令处理更加优雅。

## 🌟 功能特性

- **重复指令拦截**：自动检测并在设定的冷却时间内拦截完全相同的重复指令。
- **智能警告机制**：在拦截周期内，仅对用户进行一次“核心逻辑混乱”的警告提醒，避免机器人自身也陷入复读。
- **白名单支持**：内置帮助指令白名单，确保用户在任何时候都能获取帮助信息。
- **可视化配置**：完美支持 AstrBot 管理面板，参数修改即时生效。

## 🛠️ 安装方法

1. 在 AstrBot 插件目录下克隆本项目：
   ```bash
   cd data/plugins
   git clone https://github.com/yuanshen-scaramouche/star anti_repeat


# 支持

- [插件开发文档](https://docs.astrbot.app/dev/star/plugin-new.html)
