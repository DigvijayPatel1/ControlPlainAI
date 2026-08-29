"""
Pytest configuration, applied before any test module is collected.

asyncpg (used via SQLAlchemy's postgresql+asyncpg driver) does not reliably
support Windows' default ProactorEventLoop — writes can silently roll back
instead of committing. Forcing SelectorEventLoop fixes it. This must run
before pytest-asyncio creates its event loop, so it lives here rather than
in the test file itself.
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())