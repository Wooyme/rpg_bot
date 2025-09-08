from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Mount

from utils.scene_tools import app as scene_tools_app
from walk_with_god.api import app as walk_with_god_api_app
from llm_api import app as llm_api_app
from image_api import app as image_api_app
if __name__ == '__main__':
    routes = [
        Mount('/scene_tools', app=scene_tools_app, name="scene_tools"),
        Mount('/walk_with_god', app=walk_with_god_api_app, name="walk_with_god"),
        Mount('/llm', app=llm_api_app, name="llm"),
        Mount('/image', app=image_api_app, name="image"),
    ]
    middleware = [
        Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    ]

    app = Starlette(routes=routes, middleware=middleware)
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9601)
