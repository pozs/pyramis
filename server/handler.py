import asyncio
import http.cookies
import json
import logging
import os
import re
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from io import BytesIO
from os import mkdir
from typing import Callable

from server import ROOT_DIR, ENV, read_request, read_collections, read_collection, run_request
from server.ws import ws_accept, ws_read_frame, ws_encode_frame
from server.ws.handler import do_ws, is_ws_exit

REQUEST_RUN_TEMPLATE_PATTERN = re.compile("/request-run-template/(\\d+)")


class HTTPHandler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.cookies = http.cookies.SimpleCookie()
        self.payload = None
        self.ws_exit = False
        super().__init__(*args, directory=os.path.join(ROOT_DIR, "static"), **kwargs)

    def do_HEAD(self):
        if self.path == "/ws":
            self.send_response(HTTPStatus.CONTINUE)
            self.end_headers()
            return

        return super().do_HEAD()

    def do_GET(self):
        if self.path == "/ws":
            self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "upgrade")
            self.send_header("Sec-WebSocket-Accept", ws_accept(self.headers.get("Sec-WebSocket-Key")))
            self.end_headers()
            asyncio.run(self.ws_loop())
            return

        return super().do_GET()

    async def ws_loop(self):
        while not self.ws_exit:
            msg = ws_read_frame(self.rfile)
            if msg is None:
                return
            if len(msg) > 0:
                await do_ws(msg, self.send_ws)

    async def send_ws(self, msg: str | bytes) -> None:
        if is_ws_exit(msg):
            self.ws_exit = True
            return
        self.wfile.write(ws_encode_frame(msg))

    def send_head(self):
        self.cookies.load(self.headers.get("Cookie", ""))
        if self.path == "/collections":
            return self.send_rendered("collections.html", self.get_collections)
        elif self.path == "/collection-form":
            return self.send_rendered("collection_form.html", self.collection_form)
        else:
            match = REQUEST_RUN_TEMPLATE_PATTERN.fullmatch(self.path)
            if match:
                return self.send_rendered("request_run.html", lambda: {
                    "response_status": int(match.group(1)),
                })
            return super().send_head()

    def do_POST(self):
        self.cookies.load(self.headers.get("Cookie", ""))
        self.payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))

        f = None
        if self.path == "/collections":
            f = self.send_rendered("collection_form.html", self.post_collections)
        elif self.path == "/collection-form":
            f = self.send_rendered("collection_form.html", self.collection_form)
        elif self.path == "/collection-run":
            f = self.send_rendered("collection_run.html", self.collection_run)
        elif self.path == "/request-form":
            f = self.send_rendered("request_form.html", self.request_form)
        elif self.path == "/requests":
            f = self.send_rendered("request_form.html", self.post_requests)
        elif self.path == "/request-run":
            f = self.send_rendered("request_run.html", self.request_run)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)
        self.send_content(f)

    def do_DELETE(self):
        self.cookies.load(self.headers.get("Cookie", ""))
        self.payload = self.rfile.read(int(self.headers.get("Content-Length", 0)))

        f = None
        if self.path == "/collections":
            f = self.send_rendered("collections.html", self.delete_collections)
        self.send_content(f)

    def send_content(self, f):
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def send_rendered(self, template_path: str, call: Callable[[], dict]) -> BytesIO:
        try:
            result = call()
            template = ENV.get_template(template_path)
            rendered = template.render(result)
        except Exception as e:
            logging.error(e)
            traceback.print_exception(e)
            error = "".join(traceback.format_exception(e))
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR)
            self.send_header("Content-Type", "text/plain")
            return self.send_finish(error)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html")
        return self.send_finish(rendered)

    def send_finish(self, data: str) -> BytesIO:
        b = data.encode("utf-8")
        self.send_header("Set-Cookie", self.cookies.output(header="", sep=""))
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        return BytesIO(b)

    def read_collections_cookie(self) -> list[str]:
        if "collections" not in self.cookies:
            return []
        values = list(dict.fromkeys(self.cookies["collections"].value.split("\n")))
        values_exists = [v for v in values if os.path.isdir(v)]
        if values != values_exists:
            self.write_collections_cookie(values_exists)
        return values_exists

    def write_collections_cookie(self, value: list[str]):
        self.cookies["collections"] = "\n".join(value)
        self.cookies["collections"]["path"] = "/"
        self.cookies["collections"]["expires"] = 34560000  # 400 days

    def get_collections(self) -> dict:
        return read_collections(self.read_collections_cookie())

    def post_collections(self) -> dict:
        new = json.loads(self.payload)
        if not "collection" in new and new["collection"]:
            raise Exception("collection not found in payload")
        if not os.path.isdir(new["collection"]):
            raise Exception("not a directory")
        with open(os.path.join(new["collection"], "meta.json"), "w") as f:
            json.dump({
                "variables": new.get("variables", []),
            }, f, indent="\t")
        dirs = self.read_collections_cookie()
        dirs.append(new["collection"])
        self.write_collections_cookie(dirs)
        return read_collection(new["collection"])

    def delete_collections(self) -> dict:
        new = json.loads(self.payload)
        if not "collection" in new and new["collection"]:
            raise Exception("collection not found in payload")
        dirs = self.read_collections_cookie()
        dirs.remove(new["collection"])
        self.write_collections_cookie(dirs)
        return read_collections(dirs)

    def collection_form(self) -> dict:
        if self.payload is None:
            return read_collection(None)
        payload = json.loads(self.payload)
        if not "collection" in payload and payload["collection"]:
            raise Exception("collection not found in payload")
        return read_collection(payload["collection"])

    def collection_run(self) -> dict:
        if self.payload is None:
            return read_collection(None)
        payload = json.loads(self.payload)
        if not "collection" in payload and payload["collection"]:
            raise Exception("collection not found in payload")
        return payload

    def request_form(self) -> dict:
        new = json.loads(self.payload)
        if not "collection" in new and new["collection"]:
            raise Exception("collection not found in payload")
        return read_request(new["collection"], new.get("request", None))

    def post_requests(self) -> dict:
        new = json.loads(self.payload)
        if not ("request" in new and new["request"] and "collection" in new and new["collection"]):
            raise Exception("request or collection not found in payload")
        path = os.path.join(new["collection"], "requests", new["request"])
        if not os.path.isdir(path):
            mkdir(path)
        with open(os.path.join(path, "meta.json"), "w") as f:
            json.dump({
                "method": new.get("method", ""),
                "url": new.get("url", ""),
                "headers": new.get("headers", []),
            }, f, indent="\t")
        payload_path = os.path.join(path, "payload.data")
        if "payload" in new and new["payload"]:
            with open(payload_path, "w") as f:
                f.write(new["payload"])
        elif os.path.isfile(payload_path):
            os.remove(payload_path)
        return read_request(new["collection"], new["request"])

    def request_run(self) -> dict:
        new = json.loads(self.payload)
        if not "collection" in new and new["collection"]:
            raise Exception("collection not found in payload")
        if not "request" in new and new["request"]:
            raise Exception("request not found in payload")
        return run_request(new["collection"], new["request"])
