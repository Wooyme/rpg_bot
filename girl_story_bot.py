import asyncio
import json
import uuid
from typing import Any

import discord
from discord import Message
from discord.ext import commands
from discord.ext.modal_paginator import ModalPaginator, PaginatorModal

from walk_with_god.story import Story, load_story

STORY_MAP = {}
OPTION_CACHE = {}
LAST_OPTIONS = {}

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
        if message.channel.id not in STORY_MAP:
            await message.reply("使用命令/init_game开始游戏")
            return
        if not isinstance(message.channel, discord.channel.DMChannel):
            await message.reply("请在私聊机器人")
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


class GameSettingModal(ModalPaginator):
    def __init__(self):
        super().__init__()
        setting_modal = PaginatorModal(title='游戏设置', required=True)
        setting_modal.add_input(label='姓名', placeholder='你的名字')
        setting_modal.add_input(label='背景', placeholder='异世界生活', required=False)
        setting_modal.add_input(label='角色', placeholder='冒险家', required=False)
        setting_modal.add_input(label='初始状态', placeholder='在旅店的房间里，刚刚睡醒', required=False)
        setting_modal.add_input(label='主线目标', placeholder='收集金币，买个房子', required=False)
        god_modal = PaginatorModal(title='众神', required=False)
        god_modal.add_item(discord.ui.Select(placeholder='选择你的神', options=[]))
        memory_modal = PaginatorModal(title='回忆', required=False)
        memory_modal.add_input(label='回忆', placeholder='第一次游戏不需要填。', required=False,
                               style=discord.TextStyle.long)
        self.add_modal(setting_modal)
        self.add_modal(memory_modal)

    async def on_finish(self, interaction: discord.Interaction[Any]) -> None:
        story_id = str(uuid.uuid4())
        name = self.modals[0].children[0].value
        background = self.modals[0].children[1].value
        role = self.modals[0].children[2].value
        state = self.modals[0].children[3].value
        main_aim = self.modals[0].children[4].value
        before_story = self.modals[1].children[0].value
        await interaction.response.send_message(
            f'正在为你初始化游戏, {name}!\n**请注意，这是一个早期版本，可能存在大量未经发现的Bug。由于开发需要，系统会不定期重启或停机，对话记录会被清空。**\n'
            f'游戏流程中会有一个邪恶的神（或者说DM）在暗中操纵女主角的命运。\n'
            f'游玩过程中，一般会提供两个选项【行动】或是【以神之名】。默认选项是【行动】，你将作为女主角说话或行动。选项【以神之名】则给你命令邪神的机会，可以直接修改后续发展。\n'
            f'由于discord的限制，选项长期没有被选择时，会出现选项失效的问题。可以使用命令/options_continue来继续上次的选项。\n'
            f'随着对话历史越来越长，大模型会不可避免的丢失上下文，游戏中后期可能出现前后不一致、胡言乱语等现象。此时只能开始新游戏。\n'
            f'对话记录会被传输到discord和bot服务器，请注意不要透露个人信息。\n'
            f'该项目在github上开源：https://github.com/Wooyme/rpg_bot',
            ephemeral=False
        )
        await interaction.channel.send(content=f"本轮游戏ID：**{story_id}**，等待游戏初始化...")
        story_manager = Story(
            story_id=story_id,
            player_name=name,
            story_background=background or "异世界生活",
            player_role=role or "冒险家",
            player_state=state or "在旅店的房间里，刚刚睡醒",
            player_main_aim=main_aim or "收集金币，买个房子")
        STORY_MAP[interaction.channel.id] = story_manager
        if before_story:
            story_manager.set_memory(before_story)
        msg = await interaction.channel.send(content="正在初始化游戏，请稍等...")

        def callback(content):
            asyncio.run_coroutine_threadsafe(msg.edit(content=content), bot.loop)

        resp, options = await asyncio.to_thread(story_manager.startup,
                                                stream_callback=callback)
        LAST_OPTIONS[interaction.channel.id] = options
        await msg.edit(content=resp)
        await interaction.channel.send(view=DropdownView(Dropdown(options)))


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
    paginator = GameSettingModal()
    await paginator.send(interaction)


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
