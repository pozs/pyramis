import asyncio
import json
from typing import Callable, Coroutine

from executor import Collection, Request
from server import run_request_async, read_collection, result_to_dict, read_request

EOT = 4
EOT_CHR = chr(EOT)
EOT_BYTE = bytes([EOT])


def is_ws_exit(msg: str | bytes) -> bool:
    return msg == EOT_CHR or msg == EOT_BYTE


async def do_ws(msg: str | bytes, send: Callable[[str | bytes], Coroutine]):
    evt = json.loads(msg)
    typ = evt.get("type", "")

    if typ == "exit":
        await send(EOT_CHR)

    elif typ == "request-run":
        collection = evt["data"]["collection"]
        request = evt["data"]["request"]
        await send(json.dumps({
            "type": "request-result",
            "data": {
                "collection": collection,
                "request": request,
                "result": await run_request_async(collection, request),
            }
        }))

    elif typ == "collection-run":
        name = evt["data"]["collection"]
        c = read_collection(name)
        r = [read_request(name, r["name"]) for r in c["requests"]]
        collection = Collection(
            variables={v["name"]: v["value"] for v in c["variables"] if v["enabled"]},
            requests=[
                Request(
                    name=n["name"],
                    method=r["method"],
                    url=r["url"],
                    headers=[(h["name"], h["value"]) for h in r["headers"] if h["enabled"]],
                    payload=r["payload"] if r["payload"] else None,
                )
                for (n, r) in zip(c["requests"], r)
            ],
        )

        total = len(c["requests"])
        done = Counter()

        await send(json.dumps({
            "type": "collection-status",
            "data": {
                "collection": name,
                "status": "started",
                "total": total,
                "done": done.at(),
            }
        }))

        await collection.run(lambda req, res: asyncio.gather(
            send(json.dumps({
                "type": "request-result",
                "data": {
                    "collection": name,
                    "request": req.name,
                    "result": result_to_dict(res),
                }
            })),
            send(json.dumps({
                "type": "collection-status",
                "data": {
                    "collection": name,
                    "status": "in-progress",
                    "total": total,
                    "done": done.inc(),
                }
            }))
        ))

        await send(json.dumps({
            "type": "collection-status",
            "data": {
                "collection": name,
                "status": "finished",
                "total": total,
                "done": done.at(),
            }
        }))

    else:
        await send(json.dumps({
            "type": "error",
            "data": {
                "message": f"Unknown event type: {typ}"
            }
        }))


class Counter:
    def __init__(self):
        self.count = 0

    def at(self) -> int:
        return self.count

    def inc(self) -> int:
        self.count += 1
        return self.count
