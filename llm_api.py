from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from llm_base import llm


async def generate(request):
    data = await request.json()
    system_prompt = data.get("system_prompt", "你是一个AI助手，请根据用户的请求生成合适的回答。")
    user_prompt = data.get("user_prompt", "")
    preset = data.get("preset", "deepseek-deepinfra")
    history = data.get("history", None)
    stop_words = data.get("stop_words", None)
    prefix_words = data.get("prefix_words", None)
    suffix_words = data.get("suffix_words", None)
    hidden_words = data.get("hidden_words", None)
    resp, _ = llm(system_prompt, user_prompt, preset, history, stop_words, prefix_words, suffix_words,
                  hidden_words=hidden_words)
    return JSONResponse({"content": resp})


routes = [
    Route('/generate', generate, methods=['POST']),
]

app = Starlette(routes=routes)
