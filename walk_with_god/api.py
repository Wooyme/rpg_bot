import os.path
import pickle

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from utils.scene_tools import highlight_text
from walk_with_god.story import Story

STORIES = {

}


def load_story(story_id):
    with open(f'db/{story_id}.pak', 'rb') as f:
        return pickle.load(f)


async def dm(request):
    data = await request.json()
    query = data.get("query", "")
    conversation_id = data.get("conversation_id", "")
    player_name = data.get("player_name", "")
    player_role = data.get("player_role", "")
    background = data.get("background", "")
    if STORIES.get(conversation_id):
        story = STORIES[conversation_id]
    elif os.path.exists(f"db/{conversation_id}.pak"):
        story = load_story(conversation_id)
        STORIES[conversation_id] = story
    else:
        story = Story(god_name="lovely_god",
                      story_id=conversation_id,
                      player_name=player_name,
                      story_background=background or "异世界故事",
                      player_role=player_role or "女冒险家",
                      player_state=query,
                      player_main_aim="无")
        STORIES[conversation_id] = story
        resp, options = story.startup(player_action=query)
        with open(f'db/{conversation_id}.pak', 'wb') as f:
            pickle.dump(story, f)
        return JSONResponse(highlight_text(resp))
    resp, options = story.play(player_action=query)
    with open(f'db/{conversation_id}.pak', 'wb') as f:
        pickle.dump(story, f)
    return JSONResponse(highlight_text(resp))


routes = [
    Route('/dm', dm, methods=['POST']),
]

app = Starlette(routes=routes)
