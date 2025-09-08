import re

import llm_base
from basic_agent import PlayAgent
from walk_with_god.god import GODS


def _extract_full_scene(resp):
    if '完整叙述' in resp:
        regex = re.compile(r'完整叙述[^:：\.\s]*[:：\.]([\s\S]+)总结叙述')
    else:
        regex = re.compile(r'完整叙述[^:：\.\s]*[:：\.]([\s\S]+)')
    attr = regex.findall(resp + '\n')
    if len(attr) == 0:
        return None
    return attr[0].replace('\n', '').replace('*', '')


def _extract_scene(resp):
    regex = re.compile(r'总结叙述[^:：\.\s]*[:：\.]([\s\S]+)等待')
    attr = regex.findall(resp + '\n')
    if len(attr) == 0:
        return None
    else:
        return attr[0].replace('\n', '').replace('*', '')


def _remove_summary_text(content, player_name):
    if f'等待{player_name}决定' in content:
        regex = re.compile(rf'(总结叙述[^:：\.\s]*[:：\.][\s\S]+)等待{player_name}决定')
    else:
        regex = re.compile(r'(总结叙述[^:：\.\s]*[:：\.][\s\S]+)')
    scenes = regex.findall(content)
    for scene in scenes:
        content = content.replace(scene, '')
    return content


def _enhanced_stream_callback(stream_callback):
    def callback(content):
        content = _extract_full_scene(content)
        stream_callback(content)

    return callback


class Story(PlayAgent):
    config_path = 'config/walk_with_god.yaml'
    name = 'story'
    model_preset = 'deepseek-deepinfra'

    def __init__(self, story_id, god_name, **kwargs):
        super().__init__(**kwargs)
        self._story_id = story_id
        self._god_name = god_name
        self.god = None
        self.current_scene = None
        self._scene_history = []
        self._scene_summary = ""

    def startup(self, stream_callback=None, **kwargs):
        if stream_callback:
            stream_callback = _enhanced_stream_callback(stream_callback)
        resp, options = super().startup(
            stream_callback, **kwargs)
        self.current_scene = _extract_scene(resp)
        resp = _extract_full_scene(resp)
        return resp, options

    def play(self, stream_callback=None, **kwargs):

        if stream_callback:
            stream_callback = _enhanced_stream_callback(stream_callback)
        if self.god is None:
            self.god = GODS[self._god_name](**self.prompt_args)
            if self._scene_summary:
                self.god._scene_summary = self._scene_summary
            god_action, _ = self.god.startup(stream_callback, scene=self.current_scene, **kwargs)
        else:
            god_action, _ = self.god.play(stream_callback, scene=self.current_scene, **kwargs)
        resp, options = super().play(stream_callback,
                                     god_action=god_action, **kwargs)

        if len(self._scene_history) > 30:
            self.open_branch('save', only=True)
        self.current_scene = _extract_scene(resp)
        self._scene_history.append(self.current_scene)
        resp = _extract_full_scene(resp)
        if len(self._scene_history) == 20:
            resp = f"{resp}\n\n[小提示]对话轮次以达到20轮。30轮对话为系统上限，将强制进入结局并归档。"
        return resp, options

    def _compress_history(self, executor):

        def summary():
            scene = ""
            for i, record in enumerate(self._scene_history):
                scene += f"{i + 1}.{record}\n"
            if self._scene_summary:
                _history = [{'role': 'user', 'content': "结束的故事：" + self._scene_summary + "\n前情提要：\n" + scene}]
            else:
                _history = [{'role': 'user', 'content': "前情提要：\n" + scene}]
            return _history

        return executor.submit(summary)

    def set_memory(self, memory):
        self._scene_summary = memory
        self.add_history('user', f"结束的故事：{memory}\n不要让结束的故事再次发生。")

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
