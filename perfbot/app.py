"""PerfBot application entry point — aiohttp web server for Bot Framework."""

import asyncio
import sys

from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter
from botbuilder.schema import Activity

from src.config import settings
from src.bot import PerfBot

# Bot Framework adapter
adapter_settings = BotFrameworkAdapterSettings(
    app_id=settings.microsoft_app_id,
    app_password=settings.microsoft_app_password,
)
adapter = BotFrameworkAdapter(adapter_settings)

# Error handler
async def on_error(context, error):
    print(f"[ERROR] {error}", file=sys.stderr)
    await context.send_activity("Sorry, something went wrong processing your request.")

adapter.on_turn_error = on_error

# Bot instance
bot = PerfBot()


# Routes
async def messages(req: web.Request) -> web.Response:
    """Main bot endpoint — receives activities from Bot Framework."""
    if "application/json" not in req.headers.get("Content-Type", ""):
        return web.Response(status=415)

    body = await req.json()
    activity = Activity().deserialize(body)

    auth_header = req.headers.get("Authorization", "")
    response = await adapter.process_activity(activity, auth_header, bot.on_turn)

    if response:
        return web.json_response(data=response.body, status=response.status)
    return web.Response(status=201)


async def health(req: web.Request) -> web.Response:
    """Health check endpoint."""
    return web.json_response({"status": "healthy", "service": "perfbot"})


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=settings.port)
