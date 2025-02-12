import pickle
import random
import re

import llm_base
from basic_agent import PlayAgent


def _extract_scene(resp):
    regex = re.compile(r'场景概括[^:：\.\s]*[:：\.]([\s\S]+)等待玩家')
    attr = regex.findall(resp + '\n')
    if len(attr) == 0:
        return None
    else:
        return attr[0].strip('*').strip()


def _remove_summary_text(content):
    if '等待玩家' in content:
        regex = re.compile(r'(场景概括[^:：\.\s]*[:：\.][\s\S]+)等待玩家')
    else:
        regex = re.compile(r'(场景概括[^:：\.\s]*[:：\.][\s\S]+)')
    scenes = regex.findall(content)
    for scene in scenes:
        content = content.replace(scene, '')
    return content


class God(PlayAgent):
    config_path = 'config/walk_with_god.yaml'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scene_history = []
        self.goodness_counter = 6
        self.sex_counter = 4

    def startup(self, stream_callback=None, **kwargs):
        if 'scene' in kwargs:
            self._scene_history.append(kwargs['scene'])
        return super().startup(self._enhance_stream_callback(stream_callback), **kwargs)

    def play(self, option, extra_input, stream_callback=None, **kwargs):
        if 'scene' in kwargs:
            self._scene_history.append(kwargs['scene'])
        if len(self._scene_history) > 30:
            self.prompt_args['gameover'] = True
        self.goodness_counter -= 1
        self.sex_counter -= 1
        if self.goodness_counter == 0:
            self.goodness_counter = random.randint(4, 8)
            return super().play(option, extra_input, self._enhance_stream_callback(stream_callback), goodness=True,
                                **kwargs)
        elif self.sex_counter == 0:

            self.sex_counter = random.randint(3, 5)
            return super().play(option, extra_input, self._enhance_stream_callback(stream_callback), sex=True, **kwargs)
        return super().play(option, extra_input, self._enhance_stream_callback(stream_callback), **kwargs)

    def _enhance_stream_callback(self, callback):

        def enhanced_callback(content):
            content = "DM思考中" + len(content) * '.'
            callback(content)

        return enhanced_callback

    def _compress_history(self, executor):
        if len(self._history) < 20:
            return None
        scene = ""
        for i, record in enumerate(self._scene_history[:-5]):
            scene += f"{i + 1}.{record}\n"
        history = [{'role': 'user', 'content': f'以下是前情提要：\n{scene}'}] + self._history[-10:]

        def summary():
            return history

        return executor.submit(summary)


class EvilGod(God):
    name = 'evil_god'


def load_story(story_id):
    with open(f'db/{story_id}.pak', 'rb') as f:
        return pickle.load(f)


class Story(PlayAgent):
    config_path = 'config/walk_with_god.yaml'
    name = 'story'

    def __init__(self, story_id, **kwargs):
        super().__init__(**kwargs)
        self._story_id = story_id
        self.evil_god = None
        self.current_scene = None
        self._scene_history = []
        self._scene_summary = ""

    def startup(self, stream_callback=None, **kwargs):
        with open(f'db/{self._story_id}.pak', 'wb') as f:
            pickle.dump(self, f)
        resp, options = super().startup(self._enhanced_stream_callback(stream_callback), **kwargs)
        self.current_scene = _extract_scene(resp)
        resp = _remove_summary_text(resp)
        return resp, options

    def play(self, option, extra_input, stream_callback=None, **kwargs):
        with open(f'db/{self._story_id}.pak', 'wb') as f:
            pickle.dump(self, f)
        if option == 'main_option_action':
            if self.evil_god is None:
                self.evil_god = EvilGod(**self.prompt_args)
                god_action, _ = self.evil_god.startup(stream_callback, scene=self.current_scene,
                                                      player_action=extra_input)
            else:
                god_action, _ = self.evil_god.play(option, extra_input, stream_callback, scene=self.current_scene)

            resp, options = super().play(option, extra_input, self._enhanced_stream_callback(stream_callback),
                                         god_action=god_action)
            if len(self._scene_history) > 30:
                self.open_branch('save', only=True)
            self.current_scene = _extract_scene(resp)
            self._scene_history.append(self.current_scene)
            resp = _remove_summary_text(resp)
            return resp, options
        elif option == 'main_option_talk2god':
            return self.evil_god.play('main_option_action', None, stream_callback, talk2god=extra_input)
        elif option == 'save_option_summary':
            resp = self.summary_all()
            return resp, []

    def _enhanced_stream_callback(self, stream_callback):
        def callback(content):
            content = _remove_summary_text(content)
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
