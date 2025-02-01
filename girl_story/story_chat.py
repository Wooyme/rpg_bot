import random

from basic_agent import PlayAgent, _extract_progress
from girl_story.quests import QuestManager
from girl_story.story_battle_chat import GirlStoryBattle
from girl_story.story_sex_chat import GirlStorySex


class GirlStory(PlayAgent):
    config_path = 'config/girl_story.yaml'
    name = 'girl_story'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        long_quests = QuestManager().kickoff_list(**kwargs)
        self._long_quests = [{'quest': quest, 'context': [], 'stage': 0} for
                             quest in long_quests]
        self._current_long_quest = 0

    def on_sub_quit(self, **kwargs):
        self._current_long_quest += 1

    def play_main(self, option, player_action):
        if option == 'main_option_quests':
            self.set_sub(GirlStoryQuest(self._long_quests[self._current_long_quest], **self.prompt_args).set_context(
                self._history[1:]))


class GirlStoryQuest(PlayAgent):
    config_path = 'config/girl_story.yaml'
    name = 'quests'

    def __init__(self, quest, **kwargs):
        super().__init__(**kwargs, quest=quest['quest'])
        self._quest = quest
        self._events = ['event_exploration_point', 'event_exploration_point', 'event_exploration_point',
                        'event_neutral_encounter', 'event_enemy_encounter']
        self._next_event = random.choice(self._events)  # , 'event_sex', 'event_talk', 'event_puzzle'])
        self.prompt_args['next_event'] = self._format_text(self._next_event)
        self.prompt_args['next_stage'] = 20

    def play(self, option, extra_input, stream_callback=None):
        resp, options = super().play(option, extra_input, stream_callback)
        if self._sub_agent is not None:
            return resp, options
        stage = _extract_progress(resp)
        if stage is not None:
            if stage >= 100:
                self.open_branch('finish', only=True)
                options = self._next_options()
            elif stage >= self.prompt_args['next_stage']:
                if self._next_event == 'event_enemy_encounter':
                    self.open_branch('battle', only=True)
                    options = self._next_options()
                elif self._next_event == 'event_neutral_encounter':
                    self.open_branch('neutral', only=True)
                    options = self._next_options()
                elif self._next_event == 'event_exploration_point':
                    self.open_branch('exploration', only=True)
                    options = self._next_options()

                self.prompt_args['next_stage'] += 20
                if self.prompt_args['next_stage'] >= 100:
                    self.prompt_args['next_stage'] = 100
                    self._next_event = 'event_finish'
                else:
                    self._next_event = random.choice(self._events)
                self.prompt_args['next_event'] = self._format_text(self._next_event)
        return resp, options

    def _set_stages(self, stage):
        pass

    def play_battle(self, option, player_action):
        if option == 'battle_option_start':
            self.set_sub(GirlStoryBattle(**self.prompt_args).set_context(self._history[-1:]))
        elif option == 'battle_option_escape':
            if random.choice([True, False]):
                return {'escape': True}
            else:
                self.set_sub(GirlStoryBattle(**self.prompt_args).set_context(self._history[-1:]))

    def play_sex(self, option, player_action):
        if option == 'sex_option_start':
            self.set_sub(GirlStorySex(**self.prompt_args).set_context(self._history[-1:]))
        elif option == 'sex_option_escape':
            if random.choice([True, False]):
                return {'escape': True}
            else:
                self.set_sub(GirlStorySex(**self.prompt_args).set_context(self._history[-1:]))

    def play_finish(self, option, player_action):
        if option == 'finish_option_end':
            self.quit()
