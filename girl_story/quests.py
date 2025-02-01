from basic_agent import BasicAgent


class QuestManager(BasicAgent):
    config_path = "config/quests.yaml"
    name = 'quests_manager'


class QuestEditor(BasicAgent):
    config_path = "config/quests.yaml"
    name = 'quests_editor'

    def kickoff_list(self, stage, **kwargs):
        return super().kickoff_list(stage=stage, **kwargs)
