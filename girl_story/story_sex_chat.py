from basic_agent import PlayAgent, _extract_progress


class GirlStorySex(PlayAgent):
    config_path = 'config/girl_story.yaml'
    name = 'sex'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def play(self, option, extra_input, stream_callback=None):
        resp, options = super().play(option, extra_input, stream_callback)
        stage = _extract_progress(resp)
        if stage is not None:
            if stage >= 100:
                self.open_branch('finish', only=True)
                options = self._next_options()
            elif stage >= 20:
                self.prompt_args['sex_view'] = True
        return resp, options

    def play_finish(self, option, player_action):
        if option == 'finish_option_end':
            self.quit()
