import json

import requests
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

with open('config.json') as f:
    llm_presets = json.load(f)['llm_presets']


async def generate(request):
    data = await request.json()
    user_prompt = data.get("user_prompt", "")
    preset = llm_presets['gemini-2.5-flash-image']
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {preset['api_key']}",
        },
        data=json.dumps({
            "model": preset['model'],  # Optional
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        })
    )
    response_json = response.json()
    return JSONResponse({'content': response_json['choices'][0]['message']['images'][0]['image_url']['url']})


routes = [
    Route('/generate', generate, methods=['POST']),
]

app = Starlette(routes=routes)
