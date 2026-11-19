"""Optional loopback-only interface; importing this module does not start a server."""

from .server import PyFASTHTTPServer, create_server

__all__ = ["PyFASTHTTPServer", "create_server"]
