"""智能伴随转发插件：
只有当机器人实际在群聊中回复了消息，或者有人与机器人私聊时，
才将【群名/用户 + 对话上下文 + 机器人回复】定向通知主人，其余杂乱群消息一律静音不打扰。
"""

import os
import asyncio
import json
import re
import time
from datetime import datetime
from pathlib import Path
from nonebot import get_bot
from nonebot.log import logger

CTX_FILE = Path("/app/data/nonebot_data/nonebot_plugin_pxchat/px_chat_context.json")
MASTER = os.environ.get("CF_MASTER", "")
_PREFIX = re.compile(r"^用户(\d+)(?:[（(]([^）)]*)[）)])?说[：:]?\s*")


def _read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


async def notify_master_bot_replied(group_id: str, bot_reply: str, group_name: str = ""):
    """当机器人回复群聊时，将前因后果伴随通知给主人"""
    try:
        bot = get_bot()
    except Exception:
        return

    # 获取该群上下文中的最近发言
    key = f"group_{group_id}"
    all_ctx = _read_json(CTX_FILE, {}).get(key, [])
    
    # 提取最近 3 条群友发言作为触发背景
    recent_dialogue = []
    for m in all_ctx[-4:]:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user":
            mm = _PREFIX.match(content)
            uname = mm.group(2) if (mm and mm.group(2)) else "群友"
            clean_text = _PREFIX.sub("", content).strip()
            # 过滤掉注入画像标签
            clean_text = re.sub(r"\[关于此人：.*?\]", "", clean_text).strip()
            if clean_text:
                recent_dialogue.append(f"{uname}: {clean_text[:80]}")
    
    context_str = "\n".join(recent_dialogue) if recent_dialogue else "（群友最新发言）"
    
    msg = (
        f"🤖【小球球群聊互动通知】\n"
        f"📍 群：{group_name or group_id} ({group_id})\n"
        f"💬 触发前文：\n{context_str}\n"
        f"------------------\n"
        f"✨ 小球球回复：\n{bot_reply}"
    )

    try:
        await bot.send_private_msg(user_id=int(MASTER), message=msg)
        logger.info(f"已将群 {group_id} 的互动伴随通知转发给主人")
    except Exception as e:
        logger.warning(f"伴随转发给主人失败: {e}")
