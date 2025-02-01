import asyncio
import json
import traceback
import uuid

import discord
from discord import Message
from discord.ext import commands

from walk_with_god.story import Story

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
        story_manager = STORY_MAP[message.channel.id]
        msg = await message.reply("正在处理，请稍等...", mention_author=True)

        def callback(content):
            asyncio.run_coroutine_threadsafe(msg.edit(content=content), self.loop)

        if message.channel.id not in OPTION_CACHE:
            if len(LAST_OPTIONS.get(message.channel.id, [])) == 1:
                OPTION_CACHE[message.channel.id] = LAST_OPTIONS[message.channel.id][0]['value']
            else:
                await message.channel.send("请先选择一个选项", view=DropdownView(Dropdown(story_manager.last_options)))
                return
        resp, options = await asyncio.to_thread(story_manager.play, OPTION_CACHE[message.channel.id], message.content,
                                                callback)
        LAST_OPTIONS[message.channel.id] = options
        OPTION_CACHE.pop(message.channel.id)
        await msg.edit(content=resp)
        await message.channel.send(view=DropdownView(Dropdown(options)))


bot = Bot()


class GameSetting(discord.ui.Modal, title='游戏设置'):
    name = discord.ui.TextInput(
        label='姓名',
        placeholder='你的名字',
    )
    background = discord.ui.TextInput(
        label='背景',
        placeholder='异世界生活',
        required=False
    )
    role = discord.ui.TextInput(
        label='角色',
        placeholder='冒险家',
        required=False
    )
    state = discord.ui.TextInput(
        label='初始状态',
        placeholder='在旅店的房间里，刚刚睡醒',
        required=False
    )
    main_aim = discord.ui.TextInput(
        label='主线目标',
        placeholder='收集金币，买个房子',
        required=False
    )

    def __init__(self):
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        story_id = str(uuid.uuid4())
        await interaction.response.send_message(
            f'正在为你初始化游戏, {self.name.value}!\n**请注意，这是一个早期版本，可能存在大量未经发现的Bug。由于开发需要，系统会不定期重启或停机，对话记录会被清空。**',
            ephemeral=True)
        await interaction.channel.send(content=f"本轮游戏ID：{story_id}，等待游戏初始化...")
        story_manager = Story(
            player_name=self.name.value,
            story_background=self.background.value or "异世界生活",
            player_role=self.role.value or "冒险家",
            player_state=self.state.value or "在旅店的房间里，刚刚睡醒",
            player_main_aim=self.main_aim.value or "收集金币，买个房子")
        STORY_MAP[interaction.channel.id] = story_manager
        msg = await interaction.channel.send(content="正在初始化游戏，请稍等,这也许会持续1-2分钟")

        def callback(content):
            asyncio.run_coroutine_threadsafe(msg.edit(content=content), bot.loop)

        resp, options = await asyncio.to_thread(story_manager.startup,
                                                stream_callback=callback)
        LAST_OPTIONS[interaction.channel.id] = options
        await msg.edit(content=resp)
        await interaction.channel.send(view=DropdownView(Dropdown(options)))

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        # Make sure we know what the error actually is
        await interaction.channel.send(f'An error occurred: {error}')
        traceback.print_exception(type(error), error, error.__traceback__)


class DropdownView(discord.ui.View):
    def __init__(self, dropdown):
        super().__init__()
        self.add_item(dropdown)


class Dropdown(discord.ui.Select):
    def __init__(self, option_list):
        options = list(map(lambda x: discord.SelectOption(label=x['label'], value=x['value']), option_list))

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
                    await interaction.channel.send(view=DropdownView(Dropdown(options)))
                    return


@bot.tree.command(description="初始化新游戏")
async def init_game(interaction: discord.Interaction):
    # Send the modal with an instance of our `Feedback` class
    # Since modals require an interaction, they cannot be done as a response to a text command.
    # They can only be done as a response to either an application command or a button press.
    await interaction.response.send_modal(GameSetting())


@bot.tree.command(description="当你使用选项多次失败时，可以试试这个")
async def options_continue(interaction: discord.Interaction):
    story_manager = STORY_MAP.get(interaction.channel.id)
    if story_manager is None:
        await interaction.response.send_message('No game is running in this channel.', ephemeral=True)
        return
    await interaction.response.send_message(view=DropdownView(Dropdown(LAST_OPTIONS[interaction.channel.id])))


@bot.tree.command(description="debug")
async def debug(interaction: discord.Interaction):
    story_manager = STORY_MAP.get(interaction.channel.id)
    if story_manager is None:
        await interaction.response.send_message('No game is running in this channel.', ephemeral=True)
        return
    await interaction.response.send_message(story_manager.debug())


if __name__ == '__main__':
    with open('config.json') as f:
        token = json.load(f)['token']
        bot.run(token)
