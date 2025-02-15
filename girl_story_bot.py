import asyncio
import json
import uuid
from typing import Any

import discord
from discord import Message, SelectOption
from discord.ext import commands
from discord.ext.modal_paginator import ModalPaginator, PaginatorModal

from walk_with_god.story import Story, load_story

STORY_MAP = {}
OPTION_CACHE = {}
LAST_OPTIONS = {}

INIT_STEPS = {}


# import pydevd_pycharm
#
# pydevd_pycharm.settrace('localhost', port=9908, stdoutToServer=True, stderrToServer=True)


class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(command_prefix=commands.when_mentioned_or('$'), intents=intents)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_message(self, message: Message, /) -> None:
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return
        if not isinstance(message.channel, discord.channel.DMChannel):
            return
        if message.channel.id in INIT_STEPS:
            for i, s in enumerate(INIT_STEPS[message.channel.id]):
                if s.get('input', None) is None:
                    if message.content == 'N':
                        s['input'] = s.get('default', None)
                    else:
                        s['input'] = message.content
                    if i + 1 < len(INIT_STEPS[message.channel.id]):
                        _next = INIT_STEPS[message.channel.id][i + 1]
                        await message.reply(
                            f"输入{_next['label']}(默认:{_next.get('default', '无')}，输入“N”使用默认):\n{_next.get('description', '')}", )
                        return
            name = INIT_STEPS[message.channel.id][0]['input']
            background = INIT_STEPS[message.channel.id][1].get('input', None)
            role = INIT_STEPS[message.channel.id][2].get('input', None)
            state = INIT_STEPS[message.channel.id][3].get('input', None)
            main_aim = INIT_STEPS[message.channel.id][4].get('input', None)
            before_story = INIT_STEPS[message.channel.id][5].get('input', None)
            god_name = (INIT_STEPS[message.channel.id][6].get('input', 'evil')).lower() + '_god'
            extra_xp = INIT_STEPS[message.channel.id][7].get('input', None)
            await message.reply(
                f'正在为你初始化游戏, {name}!\n**请注意，这是一个早期版本，可能存在大量未经发现的Bug。由于开发需要，系统会不定期重启或停机，对话记录会被清空。**\n'
                f'游戏流程中会有一个神（或者说DM）在暗中操纵女主角的命运。\n'
                f'游玩过程中，一般会提供两个选项【行动】或是【以神之名】。默认选项是【行动】，你将作为女主角说话或行动。选项【以神之名】则给你命令邪神的机会，可以直接修改后续发展。\n'
                f'由于discord的限制，选项长期没有被选择时，会出现选项失效的问题。可以使用命令/options_continue来继续上次的选项。\n'
                f'随着对话历史越来越长，大模型会不可避免的丢失上下文，游戏中后期可能出现前后不一致、胡言乱语等现象。此时只能开始新游戏。\n'
                f'对话记录会被传输到discord和bot服务器，请注意不要透露个人信息。\n'
                f'该项目在github上开源：https://github.com/Wooyme/rpg_bot',
            )
            story_id = str(uuid.uuid4())
            await message.channel.send(content=f"本轮游戏ID：**{story_id}**，等待游戏初始化...")
            story_manager = Story(
                god_name=god_name,
                story_id=story_id,
                player_name=name,
                story_background=background or "异世界故事",
                player_role=role or "女冒险家",
                player_state=state or "在旅店的房间里，正要准备出门寻找任务",
                player_main_aim=main_aim or "收集金币，买个房子",
                extra_xp=extra_xp)
            STORY_MAP[message.channel.id] = story_manager
            INIT_STEPS.pop(message.channel.id)
            if before_story:
                story_manager.set_memory(before_story)
            msg = await message.channel.send(content="正在初始化游戏，请稍等...")

            def callback(content):
                asyncio.run_coroutine_threadsafe(msg.edit(content=content), bot.loop)

            resp, options = await asyncio.to_thread(story_manager.startup,
                                                    stream_callback=callback)
            LAST_OPTIONS[message.channel.id] = options
            await msg.edit(content=resp)
            await message.channel.send(view=DropdownView(Dropdown(options)))
            return
        if message.channel.id not in STORY_MAP:
            await message.reply("使用命令/init_game开始游戏")
            return
        story_manager = STORY_MAP[message.channel.id]
        msg = await message.reply("正在处理，请稍等...", mention_author=True)

        def callback(content):
            asyncio.run_coroutine_threadsafe(msg.edit(content=content), self.loop)

        if message.channel.id not in OPTION_CACHE:
            option = story_manager.last_options()[0]['value']
        else:
            option = OPTION_CACHE[message.channel.id]
            OPTION_CACHE.pop(message.channel.id)
        resp, options = await asyncio.to_thread(story_manager.play, option, message.content,
                                                callback)
        LAST_OPTIONS[message.channel.id] = options

        await msg.edit(content=resp)
        if len(options) > 0:
            await message.channel.send(view=DropdownView(Dropdown(options)))


bot = Bot()


class DropdownView(discord.ui.View):
    def __init__(self, dropdown):
        super().__init__()
        self.add_item(dropdown)


class Dropdown(discord.ui.Select):
    def __init__(self, option_list):
        options = list(map(lambda x: discord.SelectOption(label=x[1]['label'], value=x[1]['value'], default=x[0] == 0),
                           enumerate(option_list)))

        super().__init__(placeholder='选择你的行动', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        for option in self.options:
            if option.value == value:
                if option.label.endswith(':'):
                    await interaction.response.send_message(
                        f"你选择了{option.label}这是个互动选项，输入你想说的或想做的。", ephemeral=False)
                    OPTION_CACHE[interaction.channel.id] = option.value
                    return
                else:
                    story_manager = STORY_MAP[interaction.channel.id]
                    await interaction.response.send_message(f"你选择了：{option.label}", ephemeral=False)
                    msg = await interaction.channel.send(content="正在处理，请稍等...")

                    def callback(content):
                        asyncio.run_coroutine_threadsafe(msg.edit(content=content), bot.loop)

                    resp, options = await asyncio.to_thread(story_manager.play, value, "",
                                                            callback)
                    LAST_OPTIONS[interaction.channel.id] = options
                    await msg.edit(content=resp)
                    if len(options) > 0:
                        await interaction.channel.send(view=DropdownView(Dropdown(options)))
                    return


@bot.tree.command(description="初始化新游戏")
async def init_game(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.channel.DMChannel):
        await interaction.response.send_message("请在私聊中使用该命令", ephemeral=True)
        return
    INIT_STEPS[interaction.channel.id] = [
        {'label': "女主角的名称", 'value': 'player_name'},
        {'label': "故事背景", 'value': 'story_background', 'default': '异世界故事'},
        {'label': "女主角的身份", 'value': 'player_role', 'default': '女冒险家'},
        {'label': "女主的初始状态", 'value': 'player_state', 'default': '在旅店的房间里，正要准备出门寻找任务'},
        {'label': "主线目标", 'value': 'player_main_aim', 'default': '收集金币，买个房子'},
        {'label': "回忆", 'value': 'before_story', 'description': "第一次游戏不需要填。", 'default': ''},
        {'label': "叙述者", 'value': 'god_name', 'default': 'lewd',
         'description': "evil: 给你制造重重困境，并以此为乐。\n"
                        "naughty: 会给你一些麻烦，但也会给你机会。\n"
                        "lewd: 一个“快乐”的故事。\n"
                        "lovely: 一个轻松愉快的故事。\n"
         },
        {'label': "特别xp", "value": "extra_xp"}
    ]
    init_step = INIT_STEPS[interaction.channel.id]
    await interaction.response.send_message(f"输入{init_step[0]['label']}(默认:{init_step[0].get('default', '无')}):",
                                            ephemeral=True)


@bot.tree.command(description="当你使用选项多次失败时，可以试试这个")
async def options_continue(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.channel.DMChannel):
        await interaction.response.send_message("请在私聊中使用该命令", ephemeral=True)
        return
    story_manager = STORY_MAP.get(interaction.channel.id)
    if story_manager is None:
        await interaction.response.send_message('No game is running in this channel.', ephemeral=True)
        return
    await interaction.response.send_message(view=DropdownView(Dropdown(story_manager.last_options())))


@bot.tree.command(description="debug")
async def debug(interaction: discord.Interaction):
    if not isinstance(interaction.channel, discord.channel.DMChannel):
        await interaction.response.send_message("请在私聊中使用该命令", ephemeral=True)
        return
    story_manager = STORY_MAP.get(interaction.channel.id)
    if story_manager is None:
        await interaction.response.send_message('No game is running in this channel.', ephemeral=True)
        return
    await interaction.response.send_message(story_manager.debug())


@bot.tree.command(description="加载游戏")
async def load(interaction: discord.Interaction, story_id: str):
    if not isinstance(interaction.channel, discord.channel.DMChannel):
        await interaction.response.send_message("请在私聊中使用该命令", ephemeral=True)
        return
    story_manager = load_story(story_id)
    STORY_MAP[interaction.channel.id] = story_manager
    await interaction.response.send_message(view=DropdownView(Dropdown(story_manager.last_options())))


if __name__ == '__main__':
    with open('config.json') as f:
        token = json.load(f)['discord_token']
        bot.run(token)
