"""Shared slowapi limiter — one instance app-wide.

Routes import this and decorate with `@limiter.limit("...")`. main.py wires
the same instance into the FastAPI app and registers the exception handler.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
