from __future__ import annotations

import json
import re
import threading
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi
from url_import import import_url

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8765
MAX_REQUEST_BYTES = 10_000
MAX_TRANSCRIPT_CHARS = 300_000
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def video_id_from_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtube-nocookie.com"}:
        raise ValueError("YouTube 영상 링크만 입력할 수 있어요.")
    if host == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif host == "www.youtube-nocookie.com":
        pieces = [part for part in parsed.path.split("/") if part]
        candidate = pieces[-1] if pieces else ""
    else:
        pieces = [part for part in parsed.path.split("/") if part]
        candidate = urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
        if not candidate and len(pieces) >= 2 and pieces[0] in {"shorts", "embed", "live"}:
            candidate = pieces[1]
    if not VIDEO_ID.fullmatch(candidate):
        raise ValueError("영상 주소를 확인해 주세요. 재생목록 주소가 아닌 동영상 링크를 넣어 주세요.")
    return candidate


def video_title(video_id: str, canonical_url: str) -> str:
    endpoint = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": canonical_url, "format": "json"})
    try:
        request = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            title = json.loads(response.read().decode("utf-8")).get("title", "")
            if isinstance(title, str) and title.strip():
                return title.strip()[:240]
    except Exception:
        pass
    return "YouTube 영상 " + video_id


def collect_transcript(video_id: str) -> tuple[str, str]:
    api = YouTubeTranscriptApi()
    tracks = list(api.list(video_id))
    if not tracks:
        raise ValueError("이 영상에는 가져올 수 있는 자막이 없어요.")

    korean = [track for track in tracks if track.language_code.lower().startswith("ko")]
    english = [track for track in tracks if track.language_code.lower().startswith("en")]
    preferred = korean or english
    if preferred:
        track = next((item for item in preferred if not item.is_generated), preferred[0])
    else:
        track = next((item for item in tracks if item.is_translatable), tracks[0])
        if track.language_code.lower()[:2] != "ko" and track.is_translatable:
            track = track.translate("ko")

    snippets = track.fetch()
    lines = []
    for snippet in snippets:
        text = re.sub(r"<[^>]*>", "", snippet.text or "").strip()
        if not text:
            continue
        seconds = max(0, int(float(snippet.start)))
        stamp = f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"
        lines.append(f"[{stamp}] {text}")
    transcript = "\n".join(lines).strip()
    if not transcript:
        raise ValueError("자막은 찾았지만 읽을 수 있는 내용이 없어요.")
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        transcript = transcript[:MAX_TRANSCRIPT_CHARS] + "\n\n[긴 영상이라 자막 일부만 저장했어요.]"
    return transcript, track.language_code


class Handler(SimpleHTTPRequestHandler):
    server_version = "NESTLocal/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format_string, *args):
        print(f"[NEST] {self.log_date_time_string()} {format_string % args}")

    def send_json(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        origin = self.headers.get("Origin")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if origin in {"null", f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        allowed_origins = {"null", f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}
        if self.path not in {"/api/youtube/transcript", "/api/import-url"} or host not in {f"{HOST}:{PORT}", f"localhost:{PORT}"} or origin not in allowed_origins:
            self.send_error(403)
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_POST(self):
        if self.path not in {"/api/youtube/transcript", "/api/import-url"}:
            self.send_json(404, {"error": "요청한 기능을 찾지 못했어요."})
            return
        host = self.headers.get("Host", "")
        if host not in {f"{HOST}:{PORT}", f"localhost:{PORT}"}:
            self.send_json(403, {"error": "로컬 NEST 주소에서만 요청할 수 있어요."})
            return
        origin = self.headers.get("Origin")
        if origin and origin not in {"null", f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"}:
            self.send_json(403, {"error": "로컬 NEST 페이지에서만 요청할 수 있어요."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("영상 링크를 확인해 주세요.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            raw_url = payload.get("url", "")
            if not isinstance(raw_url, str):
                raise ValueError("영상 링크를 확인해 주세요.")
            if self.path == "/api/import-url":
                self.send_json(200, import_url(raw_url))
                return
            video_id = video_id_from_url(raw_url)
            canonical_url = f"https://www.youtube.com/watch?v={video_id}"
            transcript, language = collect_transcript(video_id)
            title = video_title(video_id, canonical_url)
            self.send_json(200, {
                "videoId": video_id,
                "url": canonical_url,
                "title": title,
                "language": language,
                "transcript": transcript,
            })
        except ValueError as error:
            self.send_json(422, {"error": str(error)})
        except Exception:
            self.send_json(502, {"error": "YouTube 자막을 가져오지 못했어요. 공개 영상인지, 자막이 있는지 확인해 주세요."})


if __name__ == "__main__":
    print(f"NEST is running at http://{HOST}:{PORT}/")
    print("Keep this window open while you use NEST.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
