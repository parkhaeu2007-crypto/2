from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.parse
import urllib.request

from youtube_transcript_api import YouTubeTranscriptApi

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
MAX_BYTES = 10_000
MAX_CHARS = 300_000


def get_video_id(value):
    parsed = urllib.parse.urlsplit(value.strip())
    host = (parsed.hostname or "").lower()
    if host not in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtube-nocookie.com"}:
        raise ValueError("YouTube 영상 링크만 입력할 수 있어요.")
    parts = [part for part in parsed.path.split("/") if part]
    candidate = parts[0] if host == "youtu.be" and parts else urllib.parse.parse_qs(parsed.query).get("v", [""])[0]
    if host != "youtu.be" and not candidate and len(parts) >= 2 and parts[0] in {"shorts", "embed", "live"}:
        candidate = parts[1]
    if host == "www.youtube-nocookie.com" and parts:
        candidate = parts[-1]
    if not VIDEO_ID.fullmatch(candidate):
        raise ValueError("영상 주소를 확인해 주세요. 재생목록 주소가 아닌 동영상 링크를 넣어 주세요.")
    return candidate


def collect_transcript(video_id):
    tracks = list(YouTubeTranscriptApi().list(video_id))
    if not tracks:
        raise ValueError("이 영상에는 가져올 수 있는 자막이 없어요.")
    korean = [track for track in tracks if track.language_code.lower().startswith("ko")]
    english = [track for track in tracks if track.language_code.lower().startswith("en")]
    preferred = korean or english
    if preferred:
        track = next((item for item in preferred if not item.is_generated), preferred[0])
    else:
        track = next((item for item in tracks if item.is_translatable), tracks[0])
        if not track.language_code.lower().startswith("ko") and track.is_translatable:
            track = track.translate("ko")
    lines = []
    for snippet in track.fetch():
        text = re.sub(r"<[^>]*>", "", snippet.text or "").strip()
        if text:
            seconds = max(0, int(float(snippet.start)))
            lines.append(f"[{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}] {text}")
    transcript = "\n".join(lines).strip()
    if not transcript:
        raise ValueError("자막은 찾았지만 읽을 수 있는 내용이 없어요.")
    if len(transcript) > MAX_CHARS:
        transcript = transcript[:MAX_CHARS] + "\n\n[긴 영상이라 자막 일부만 저장했어요.]"
    return transcript, track.language_code


def get_title(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    endpoint = "https://www.youtube.com/oembed?" + urllib.parse.urlencode({"url": url, "format": "json"})
    try:
        request = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            title = json.loads(response.read().decode("utf-8")).get("title", "")
            if isinstance(title, str) and title.strip():
                return title.strip()[:240]
    except Exception:
        pass
    return "YouTube 영상 " + video_id


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
            if length <= 0 or length > MAX_BYTES:
                raise ValueError("영상 링크를 확인해 주세요.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            raw_url = payload.get("url", "")
            if not isinstance(raw_url, str):
                raise ValueError("영상 링크를 확인해 주세요.")
            video_id = get_video_id(raw_url)
            transcript, language = collect_transcript(video_id)
            self.reply(200, {
                "videoId": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": get_title(video_id),
                "language": language,
                "transcript": transcript,
            })
        except ValueError as error:
            self.reply(422, {"error": str(error)})
        except Exception:
            self.reply(502, {"error": "YouTube 자막을 가져오지 못했어요. 공개 영상인지, 자막이 있는지 확인해 주세요."})
