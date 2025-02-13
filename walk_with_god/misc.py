from basic_agent import BasicAgent


class Moderator(BasicAgent):
    config_path = "config/misc.yaml"
    name = 'moderator'
    model_preset = 'deepseek-r1-32b'

    def kickoff(self, **kwargs):
        result = super().kickoff(**kwargs)
        if '否' in result:
            return False
        else:
            return True
