import random

from basic_agent import PlayAgent


class GirlStoryBattle(PlayAgent):
    config_path = 'config/girl_story.yaml'
    name = 'battle'

    def __init__(self, **kwargs):
        self.damage_count = 0
        self.injured_count = 0
        super().__init__(**kwargs)

    def play_main(self, option, player_action):
        extra_args = {}
        if option == 'main_option_attack':
            if random.choice([True, False]):
                extra_args['attack_success'] = True
                self.damage_count += 1
            else:
                extra_args['attack_failed'] = True
        elif option == 'main_option_defend':
            if random.choice([True, False]):
                extra_args['defend_success'] = True
            else:
                extra_args['defend_failed'] = True
                self.injured_count += 1
        elif option == 'main_option_escape':
            if random.choice([True, False]):
                extra_args['escape_success'] = True
                self.injured_count += 1
            else:
                extra_args['escape_failed'] = True
        else:
            raise ValueError(f"Unknown option: {option}")
        if self.damage_count >= 1:
            extra_args['win'] = True
            self.quit(win=True)
        elif self.injured_count >= 3:
            extra_args['lose'] = True
            self.quit(lose=True)
        return extra_args
