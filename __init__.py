from nonebot.rule import to_me
from nonebot import on_message, on_command
from nonebot import get_driver
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.permission import GROUP_OWNER, GROUP_ADMIN
from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment, GroupMessageEvent, Bot, Message

from .chatglm import Chatglm
from .config_ import config
import json
import os

preset_dir = os.path.dirname(config.preset_path)
preset_path = config.preset_path
if not os.path.exists(preset_path):
    if not os.path.exists(preset_dir):
        os.makedirs(preset_dir)
    if not preset_path.endswith(".json"):
        preset_path = os.path.join(preset_dir, "preset.json")
    with open(preset_path, "w") as file:
        data = {"default": "", "名称": "预设"}
        json.dump(data, file, indent=2)
        logger.warning(f"未检测到预设文件，已创建{preset_path}")
        preset = ["default", ""]
else:
    if config.preset_path.endswith(".json"):
        with open(config.preset_path, "r") as file:
            preset = ["default", json.load(file)["default"]]
    else:
        preset_path = os.path.join(preset_dir, "preset.json")
        with open(preset_path, "w") as file:
            data = {"default": "", "名称": "预设"}
            json.dump(data, file, indent=2)
            logger.warning(f"未检测到预设文件，已创建{preset_path}")
            preset = ["default", ""]
            preset_path = os.path.join(preset_dir, "preset.json")
conversation_list = []
chatglm_ = Chatglm(token=config.token,refresh_token=config.refresh_token,acw_tc=config.acw_tc,
                   assistant_id=config.assistant_id)
max_len = config.max_len
with open(config.preset_path, "r") as file:
    prset = json.load(file)
driver = get_driver()


@driver.on_bot_connect
async def __init__(bot: Bot):
    logger.info(f"成功连接至{bot.self_id}")


async def get_preset():
    with open(preset_path, "r") as file:
        return json.load(file)


async def preset_handle(id: int):
    data = await get_preset()
    message = Message()
    number = 1
    # for key,value in data.items():
    #     message.append(MessageSegment.node_custom(id,"",f"序号：{number}\n预设名：{key}\n内容：\n{value}"))
    for key in data.keys():
        message.append(MessageSegment.node_custom(
            id, "", f"序号：{number}\n预设名：{key}"))
        number += 1
    return message
tome = on_message(rule=to_me(), priority=999)

async def recommand():
    recommand=await chatglm_.recommand(chatglm_.conversation_id)
    if recommand:
        message="推荐回复："
        for n in recommand:
            message+=n+"\n"
        return message
    else:
        return False
@tome.handle()
async def _(event: MessageEvent, bot: Bot):
    message = event.get_message().extract_plain_text()
    data = await chatglm_.send(message=message, conversation_id=chatglm_.conversation_id)
    reply = data.get("text")
    if len(reply) > max_len:  # type: ignore
        forward = Message(MessageSegment.node_custom(
            event.self_id, "", reply))  # type: ignore
        if isinstance(event, GroupMessageEvent):
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=forward)
            next_recommand=await recommand()
            if next_recommand:
                await tome.finish(next_recommand)
        else:
            await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=forward)
            next_recommand=await recommand()
            if next_recommand:
                await tome.finish(next_recommand)
        # await tome.finish(forward)
    else:
        await tome.send(reply) # type: ignore
        next_recommand=await recommand()
        if next_recommand:
            await tome.finish(next_recommand)

change_preset = on_command("切换预设", priority=997, block=True,
                           permission=SUPERUSER | GROUP_OWNER | GROUP_ADMIN)


@change_preset.handle()
async def _(event: MessageEvent, bot: Bot):
    message = await preset_handle(event.self_id)
    if isinstance(event, GroupMessageEvent):
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=message)
        await change_preset.pause("请选择序号，发送0取消选择")
    else:
        await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=message)
        await change_preset.pause("请选择序号，发送0取消选择")


@change_preset.handle()
async def _(event: MessageEvent):
    global preset
    try:
        number = int(event.get_plaintext())
    except:
        await change_preset.finish("参数错误")
    if number == 0:
        await change_preset.finish("已取消选择")
    data = await get_preset()
    key = list(data.keys())[number-1]
    value = data[key]
    preset = [key, value]
    await change_preset.finish(f"已修改预设为：{key}")


set_access_token = on_command(
    "/access", priority=996, block=True, permission=SUPERUSER)


@set_access_token.handle()
async def _(args: Message = CommandArg()):
    arg = args.extract_plain_text()
    if arg:
        chatglm_.token = arg
        await set_access_token.finish("设置access_token成功")
    else:
        await set_access_token.finish("未检测到token")
# permission=GROUP_ADMIN|GROUP_OWNER|SUPERUSER
refresh_conversation = on_command("刷新会话", priority=995, block=True)


@refresh_conversation.handle()
async def _():
    data = await chatglm_.send(message=preset[1])
    if isinstance(data, dict):
        reply = f"刷新会话成功\n使用预设：{preset[0]}\nid:{data.get('conversation_id')}"
        await refresh_conversation.send(reply)
        await refresh_conversation.finish(data.get("text"))
    else:
        await refresh_conversation.finish(data)

change_conversation = on_command(
    "切换会话", priority=994, block=True, permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)


@change_conversation.handle()
async def _(event: MessageEvent, bot: Bot):
    global conversation_list
    page=1
    tmp=[]
    while 1:
        data = await chatglm_.get_conversations(page=page)
        tmp.append(*data[0])# type: ignore
        if not data[1]:# type: ignore
            break
        page+=1
    conversation_list=tmp
    message = Message()
    number = 1
    for n in tmp:
        message.append(MessageSegment.node_custom(
            event.self_id, "", f"序号：{number}\n标题:{n.get('title')}\nid:{n.get('conversation_id')}"))
        number += 1
    # else:
    #     await change_conversation.finish(f"查询会话发生错误：{data}")
    if isinstance(event, GroupMessageEvent):
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=message)
        await change_conversation.pause("请选择序号，发送0取消选择")
    else:
        await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=message)
        await change_conversation.pause("请选择序号，发送0取消选择")


@change_conversation.handle()
async def _(event: MessageEvent):
    global conversation_list
    try:
        number = int(event.get_plaintext())
    except:
        await change_conversation.finish("参数错误")
    if number == 0:
        await change_conversation.finish("已取消选择")

    chatglm_.conversation_id = conversation_list[number-1].get("conversation_id")
    title = conversation_list[number-1].get("title")
    await change_conversation.finish(f"已修改会话为：\n标题:{title}\nid:{chatglm_.conversation_id}")

add_preset = on_command("添加预设", priority=993, block=True,
                        permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)


@add_preset.handle()
async def _():
    await add_preset.pause("请发送预设名称和内容\n示例：名称 内容")


@add_preset.handle()
async def _(event: MessageEvent):
    content = event.get_plaintext().split()
    if len(content) != 2:
        await add_preset.finish("参数错误")
    with open(config.preset_path, "r+") as file:
        data = json.load(file)
        data.update({content[0]: content[1]})
        file.seek(0)
        json.dump(data, file, indent=2)
        await add_preset.finish(f"添加预设{content[0]}成功")

del_preset = on_command("删除预设", priority=992, block=True,
                        permission=GROUP_ADMIN | GROUP_OWNER | SUPERUSER)


@del_preset.handle()
async def _(event: MessageEvent, bot: Bot):
    reply = await preset_handle(event.self_id)
    if isinstance(event, GroupMessageEvent):
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=reply)
        await del_preset.pause("请选择序号，发送0取消选择")
    else:
        await bot.call_api("send_private_forward_msg", user_id=event.user_id, messages=reply)
        await del_preset.pause("请选择序号，发送0取消选择")


@del_preset.handle()
async def _(event: MessageEvent):
    arg = event.get_plaintext()
    try:
        arg = int(arg)
    except:
        await del_preset.finish("参数错误")
    with open(config.preset_path, "r+") as file:
        data = json.load(file)
        key = list(data.keys())[arg-1]
        del data[key]
        file.seek(0)
        json.dump(data, file, indent=2)
        file.truncate()
        await del_preset.finish(f"删除预设{key}成功")

refresh_session = on_command("/auth", priority=996, block=True, permission=SUPERUSER)

@refresh_session.handle()
async def _(args: Message = CommandArg()):
    token = args.extract_plain_text()
    if token:
        result = await chatglm_.refresh(refresh_token=token)
        if result:
            await refresh_session.finish("刷新token成功")
    else:
        result = await chatglm_.refresh(refresh_token=chatglm_.refresh_token)
        if result:
            await refresh_session.finish("刷新token成功")