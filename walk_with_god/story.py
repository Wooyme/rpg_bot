import re

from basic_agent import PlayAgent, _remove_options


def _extract_scene(resp):
    regex = re.compile(r'场景概括[^:：\.\s]*[:：\.]([\s\S]+)等待玩家')
    attr = regex.findall(resp + '\n')
    if len(attr) == 0:
        return None
    else:
        return attr[0].strip().strip('*')


def _remove_summary_text(content):
    if '等待玩家' in content:
        regex = re.compile(r'(场景概括[^:：\.\s]*[:：\.][\s\S]+)等待玩家')
    else:
        regex = re.compile(r'(场景概括[^:：\.\s]*[:：\.][\s\S]+)')
    scenes = regex.findall(content + '\n')
    for scene in scenes:
        content = content.replace(scene, '')
    return content


class EvilGod(PlayAgent):
    config_path = 'config/walk_with_god.yaml'
    name = 'evil_god'

    def _enhance_stream_callback(self, callback):
        def enhanced_callback(content):
            content = "DM：" + content.split('。')[0]
            callback(content)

        return enhanced_callback


class Story(PlayAgent):
    config_path = 'config/walk_with_god.yaml'
    name = 'story'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.god = None
        self.current_scene = None
        self._scene_history = []

    def startup(self, stream_callback=None, **kwargs):
        resp, options = super().startup(self._enhanced_stream_callback(stream_callback), **kwargs)
        self.current_scene = _extract_scene(resp)
        return resp, options

    def play(self, option, extra_input, stream_callback=None, **kwargs):
        if option == 'main_option_action':
            if self.god is None:
                self.god = EvilGod(**self.prompt_args)
                god_action, _ = self.god.startup(stream_callback, scene=self.current_scene, player_action=extra_input)
            else:
                god_action, _ = self.god.play(option, extra_input, stream_callback, scene=self.current_scene)
            resp, options = super().play(option, extra_input, self._enhanced_stream_callback(stream_callback),
                                         god_action=god_action)
            self.current_scene = _extract_scene(resp)
            self._scene_history.append(self.current_scene)
            resp = _remove_summary_text(resp)
            return resp, options
        elif option == 'main_option_talk2god':
            return self.god.play(option, None, stream_callback, talk2god=extra_input)

    def _enhanced_stream_callback(self, stream_callback):
        def callback(content):
            content = _remove_summary_text(content)
            stream_callback(content)

        return callback

    def _compress_history(self, executor):
        keep = [self._history[0]]
        scene = ""
        for i, record in enumerate(self._scene_history):
            scene += f"{i + 1}.{record}\n"
        history = keep + [{'role': 'user', 'content': f'以下是前情提要：\n{scene}'}]

        def summary():
            return history

        return executor.submit(summary)
