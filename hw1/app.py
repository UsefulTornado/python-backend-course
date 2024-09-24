import json
import math
from http import HTTPStatus
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qsl

from hw1.utils import fibonacci, is_int_number


class HTTPResponse:
    @staticmethod
    async def send(
        send_fn: Callable[[dict[str, Any]], Awaitable[None]],
        status: HTTPStatus,
        body: str,
    ) -> None:
        await send_fn(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [[b"content-type", b"text/plain"]],
            }
        )
        await send_fn({"type": "http.response.body", "body": body.encode()})


async def get_query_body(receive_fn):
    body = []

    while True:
        chunk = await receive_fn()
        body.append(chunk["body"])

        if not chunk["more_body"]:
            break

    return b"".join(body)


async def handle_factorial(send, scope):
    params = dict(parse_qsl(scope["query_string"].decode()))

    if "n" not in params or not is_int_number(params["n"]):
        return await HTTPResponse.send(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid input."
        )

    if int(params["n"]) < 0:
        return await HTTPResponse.send(send, HTTPStatus.BAD_REQUEST, "Invalid input.")

    result = math.factorial(int(params["n"]))

    await HTTPResponse.send(send, HTTPStatus.OK, f'{{"result": {result}}}')


async def handle_fibonacci(send, scope):
    path = scope["path"].strip("/")
    path_parts = path.split("/")

    if len(path_parts) != 2 or not is_int_number(path_parts[1]):
        return await HTTPResponse.send(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid input."
        )

    if int(path_parts[1]) < 0:
        return await HTTPResponse.send(send, HTTPStatus.BAD_REQUEST, "Invalid input.")

    result = fibonacci(int(path_parts[1]))

    return await HTTPResponse.send(send, HTTPStatus.OK, f'{{"result": {result}}}')


async def handle_mean(send, receive, scope):
    body = (await get_query_body(receive)).decode()
    try:
        data = json.loads(body)
    except Exception:
        return await HTTPResponse.send(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid input."
        )

    if not isinstance(data, list) or not all(isinstance(x, (int, float)) for x in data):
        return await HTTPResponse.send(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid input."
        )

    if len(data) == 0:
        return await HTTPResponse.send(
            send, HTTPStatus.BAD_REQUEST, "No data provided."
        )

    result = sum(data) / len(data)

    return await HTTPResponse.send(send, HTTPStatus.OK, f'{{"result": {result:.2f}}}')


async def app(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    path = scope["path"]
    method = scope["method"]

    if path == "/factorial" and method == "GET":
        await handle_factorial(send, scope)
    elif path.startswith("/fibonacci/") and method == "GET":
        await handle_fibonacci(send, scope)
    elif path == "/mean" and method == "GET":
        await handle_mean(send, receive, scope)
    else:
        await HTTPResponse.send(send, HTTPStatus.NOT_FOUND, "404 Not Found")
