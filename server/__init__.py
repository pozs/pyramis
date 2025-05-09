import asyncio
import json
import os

from jinja2 import Environment, PackageLoader, select_autoescape

from executor import Collection, Request, Result

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV = Environment(
    loader=PackageLoader("server", "templates"),
    autoescape=select_autoescape(),
)


def read_collections(collections: list[str]):
    return {
        "collections": [read_collection(c) for c in collections]
    }


def read_collection(collection: str | None) -> dict:
    if collection is None:
        return {
            "name": "",
            "collection": "",
            "variables": [],
            "requests": []
        }

    requests = []
    path = os.path.join(collection, "requests")
    if os.path.isdir(path):
        requests = [
            {"name": r} for r in os.listdir(path) if os.path.isdir(os.path.join(path, r))
        ]
    meta = {}
    try:
        with open(os.path.join(collection, "meta.json"), "r") as f:
            meta = json.load(f)
    except FileNotFoundError:
        pass

    return {
        "name": os.path.basename(collection),
        "collection": collection,
        "variables": meta.get("variables", []),
        "requests": requests
    }


def read_request(collection: str, request: str | None) -> dict:
    if request is None:
        return {
            "collection": collection,
            "request": "",
            "method": "",
            "url": "",
            "headers": [],
            "payload": "",
        }

    path = os.path.join(collection, "requests", request)
    with open(os.path.join(path, "meta.json"), "r") as f:
        meta = json.load(f)

    payload = ""
    if os.path.isfile(os.path.join(path, "payload.data")):
        with open(os.path.join(path, "payload.data"), "r") as f:
            payload = f.read()

    return {
        "collection": collection,
        "request": request,
        "method": meta.get("method", ""),
        "url": meta.get("url", ""),
        "headers": meta.get("headers", []),
        "payload": payload,
    }


def run_request(collection: str, request: str) -> dict:
    return asyncio.run(run_request_async(collection, request))


async def run_request_async(collection: str, request: str) -> dict:
    collection_read = read_collection(collection)
    request_read = read_request(collection, request)
    return result_to_dict(await Collection(
        variables={v["name"]: v["value"] for v in collection_read["variables"] if v["enabled"]},
        requests=[],
    ).run_single(Request(
        name=request,
        method=request_read["method"],
        url=request_read["url"],
        headers=[(h["name"], h["value"]) for h in request_read["headers"] if h["enabled"]],
        payload=request_read["payload"] if request_read["payload"] else None,
    )))


def result_to_dict(result: Result) -> dict:
    return {
        "request_method": result.request_method,
        "request_url": result.request_url,
        "request_headers": format_headers(result.request_headers),
        "request_payload": result.request_payload.decode("utf-8") if result.request_payload else None,
        "response_status": result.response_status,
        "response_headers": format_headers(result.response_headers),
        "response_payload": result.response_payload.decode("utf-8") if result.response_payload else None,
    }


def format_headers(headers: list[tuple[str, str]]) -> str:
    return "\n".join(f"{k}: {v}" for k, v in headers)
