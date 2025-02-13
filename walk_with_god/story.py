import pickle
import re

import llm_base
from basic_agent import PlayAgent
from walk_with_god.god import EvilGod, GODS
from walk_with_god.misc import Moderator


def _extract_scene(resp):
    regex = re.compile(r'场景概括[^:：\.\s]*[:：\.]([\s\S]+)等待')
    attr = regex.findall(resp + '\n')
    if len(attr) == 0:
        return None
    else:
        return attr[0].replace('\n', '').replace('*', '')


def _remove_summary_text(content, player_name):
    if f'等待{player_name}回复' in content:
        regex = re.compile(rf'(场景概括[^:：\.\s]*[:：\.][\s\S]+)等待{player_name}回复')
    else:
        regex = re.compile(r'(场景概括[^:：\.\s]*[:：\.][\s\S]+)')
    scenes = regex.findall(content)
    for scene in scenes:
        content = content.replace(scene, '')
    return content


def load_story(story_id):
    with open(f'db/{story_id}.pak', 'rb') as f:
        return pickle.load(f)


class Story(PlayAgent):
    config_path = 'config/walk_with_god.yaml'
    name = 'story'

    def __init__(self, story_id, god_name, **kwargs):
        super().__init__(**kwargs)
        self._story_id = story_id
        self._god_name = god_name
        self.god = None
        self.current_scene = None
        self._scene_history = []
        self._scene_summary = ""

    def startup(self, stream_callback=None, **kwargs):
        with open(f'db/{self._story_id}.pak', 'wb') as f:
            pickle.dump(self, f)
        resp, options = super().startup(self._enhanced_stream_callback(stream_callback), **kwargs)
        self.current_scene = _extract_scene(resp)
        resp = _remove_summary_text(resp, self.prompt_args['player_name'])
        return resp, options

    def play(self, option, extra_input, stream_callback=None, **kwargs):
        with open(f'db/{self._story_id}.pak', 'wb') as f:
            pickle.dump(self, f)
        if option == 'main_option_action':
            if self.god is None:
                self.god = GODS[self._god_name](**self.prompt_args)
                god_action, _ = self.god.startup(stream_callback, scene=self.current_scene,
                                                 player_action=extra_input)
            else:
                god_action, _ = self.god.play(option, extra_input, stream_callback, scene=self.current_scene)
            self.god.prompt_args['talk2god'] = None
            resp, options = super().play(option, extra_input, self._enhanced_stream_callback(stream_callback),
                                         god_action=god_action)

            if len(self._scene_history) > 30:
                self.open_branch('save', only=True)
            self.current_scene = _extract_scene(resp)
            self._scene_history.append(self.current_scene)
            resp = _remove_summary_text(resp, self.prompt_args['player_name'])
            if len(self._scene_history) == 10:
                self.open_branch('save')
                resp = f"{resp}\n\n[小提示]归档功能已启用。"
            if len(self._scene_history) == 20:
                resp = f"{resp}\n\n[小提示]对话轮次以达到20轮。30轮对话为系统上限，将强制进入结局并归档。"
            return resp, options
        elif option == 'main_option_talk2god':
            self.god.prompt_args['talk2god'] = extra_input
            return "神听到了", self._next_options()
        elif option == 'save_option_summary':
            resp = self.summary_all()
            return resp, []

    def _enhanced_stream_callback(self, stream_callback):
        def callback(content):
            content = _remove_summary_text(content, self.prompt_args['player_name'])
            stream_callback(content)

        return callback

    def _compress_history(self, executor):

        def summary():
            scene = ""
            for i, record in enumerate(self._scene_history):
                scene += f"{i + 1}.{record}\n"
            if self._scene_summary:
                _history = [{'role': 'user', 'content': "过去的故事：" + self._scene_summary + "\n前情提要：\n" + scene}]
            else:
                _history = [{'role': 'user', 'content': "前情提要：\n" + scene}]
            return _history

        return executor.submit(summary)

    def set_memory(self, memory):
        self._scene_summary = memory
        self.add_history('user', f"过去的故事：{memory}")

    def summary_all(self):
        scene = ""
        for i, record in enumerate(self._scene_history):
            scene += f"{i + 1}.{record}\n"
        history = [{'role': 'user', 'content': scene}]
        resp, _ = llm_base.llm("你要压缩对话记录",
                               self._summary_prompt(),
                               history=history,
                               preset=self.model_preset)
        self.logger.info(f"Summary: {resp}")
        self._scene_summary = resp
        return resp

    def debug(self):
        return '\n'.join(self._scene_history)
