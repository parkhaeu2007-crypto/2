from http.server import BaseHTTPRequestHandler
import json
from url_import import import_url

class handler(BaseHTTPRequestHandler):
    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "POST, OPTIONS")
        self.end_headers()

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 10_000:
                raise ValueError("링크를 확인해 주세요.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            url = payload.get("url", "")
            if not isinstance(url, str):
                raise ValueError("링크를 확인해 주세요.")
            self.reply(200, import_url(url))
        except ValueError as error:
            self.reply(422, {"error": str(error)})
        except Exception:
            self.reply(502, {"error": "페이지를 읽지 못했어요. 공개된 웹페이지나 PDF 링크인지 확인해 주세요."})
