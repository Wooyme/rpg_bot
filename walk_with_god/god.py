import random

from basic_agent import PlayAgent


class God(PlayAgent):
    config_path = 'config/walk_with_god.yaml'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scene_history = []
        self.goodness_counter = 6
        self._scene_summary = ""

    def startup(self, stream_callback=None, **kwargs):
        if 'scene' in kwargs:
            self._scene_history.append(kwargs['scene'])
        if self._scene_summary:
            self.add_history('user', f"结束的故事：{self._scene_summary}\n不要让结束的故事再次发生。")
        resp, options = super().startup(self._enhance_stream_callback(stream_callback), **kwargs)
        return resp.replace('\n', '').replace('\r', ''), options

    def play(self, option, extra_input, stream_callback=None, **kwargs):
        if 'scene' in kwargs:
            self._scene_history.append(kwargs['scene'])
        if len(self._scene_history) > 30:
            self.prompt_args['gameover'] = True
        self.goodness_counter -= 1
        if self.goodness_counter == 0:
            self.goodness_counter = random.randint(4, 8)
            resp, options = super().play(option, extra_input, self._enhance_stream_callback(stream_callback),
                                         goodness=True,
                                         **kwargs)
        else:
            resp, options = super().play(option, extra_input, self._enhance_stream_callback(stream_callback),
                                         **kwargs)
        return resp.replace('\n', '').replace('\r', ''), options

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
        if self._scene_summary:
            history.insert(0, {'role': 'user', 'content': f"过去的故事：{self._scene_summary}"})

        def summary():
            return history

        return executor.submit(summary)


class EvilGod(God):
    name = 'evil_god'


class NaughtyGod(God):
    name = 'naughty_god'


class LewdGod(God):
    name = 'lewd_god'


class LovelyGod(God):
    name = 'lovely_god'


class SlutGod(God):
    name = 'slut_god'


GODS = {
    'evil_god': EvilGod,
    'naughty_god': NaughtyGod,
    'lewd_god': LewdGod,
    'lovely_god': LovelyGod,
    'slut_god': SlutGod
}
