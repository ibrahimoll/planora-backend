from __future__ import annotations

import inspect

from fastapi.routing import APIRoute


REQUIRED_PUSH_SERVICE_FUNCTIONS = {
    "register_device_token",
    "get_my_device_tokens",
    "deactivate_my_device_token",
    "heartbeat_device_token",
    "get_or_create_notification_preferences",
    "update_notification_preferences",
    "deactivate_current_device_tokens",
}


def test_push_notification_router_imports_and_exposes_heartbeat_route() -> None:
    from app.routers.push_notification_routes import router

    heartbeat_routes = [
        route
        for route in router.routes
        if isinstance(route, APIRoute)
        and route.path.endswith("/device-tokens/current/heartbeat")
        and "PATCH" in route.methods
    ]

    assert heartbeat_routes, "Push notification heartbeat route is not registered."


def test_push_notification_service_exports_service_functions() -> None:
    import app.services.push_notification_service as push_service

    local_functions = {
        name
        for name, value in inspect.getmembers(push_service, inspect.isfunction)
        if value.__module__ == push_service.__name__
    }

    missing_functions = REQUIRED_PUSH_SERVICE_FUNCTIONS - local_functions

    assert not missing_functions, (
        "push_notification_service.py is missing service functions: "
        f"{sorted(missing_functions)}"
    )
