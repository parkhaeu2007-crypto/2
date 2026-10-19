"""Fetch readable text from public web pages and PDF URLs for NEST."""
from html.parser import HTMLParser
from io import BytesIO
import ipaddress
import socket
import urllib.parse
import urllib.request

MAX_BYTES = 6_000_000


def validate_public_url(value):
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("http 또는 https로 시작하는 공개 링크를 입력해 주세요.")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("공개 웹페이지 링크만 가져올 수 있어요.")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError as error:
        raise ValueError("링크에 연결할 수 없어요. 주소를 확인해 주세요.") from error
    if not addresses or any(not ipaddress.ip_address(address.split("%")[0]).is_global for address in addresses):
        raise ValueError("공개 웹페이지 링크만 가져올 수 있어요.")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PageText(HTMLParser):
    BLOCKS = {"article", "p", "div", "section", "main", "h1", "h2", "h3", "h4", "li", "br", "tr"}
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title_parts, self.title = [], [], False
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip_depth += 1
        if tag == "title":
            self.title = True
        if not self.skip_depth and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self.title = False
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        if not self.skip_depth and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.title:
            self.title_parts.append(data)
        if not self.skip_depth:
            self.parts.append(data)


def import_url(value):
    url = validate_public_url(value)
    opener = urllib.request.build_opener(SafeRedirect())
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; NESTStudy/1.0)", "Accept": "text/html,application/pdf,text/plain;q=0.9,*/*;q=0.5"})
    with opener.open(request, timeout=18) as response:
        content_type = response.headers.get_content_type().lower()
        body = response.read(MAX_BYTES + 1)
        final_url = validate_public_url(response.geturl())
        charset = response.headers.get_content_charset() or "utf-8"
    if len(body) > MAX_BYTES:
        raise ValueError("파일이 너무 커서 가져올 수 없어요. 6MB 이하 링크를 사용해 주세요.")
    if content_type == "application/pdf" or body[:5] == b"%PDF-":
        try:
            from pypdf import PdfReader
            reader = PdfReader(BytesIO(body))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            title = reader.metadata.title if reader.metadata and reader.metadata.title else "PDF 자료"
        except Exception as error:
            raise ValueError("PDF에서 텍스트를 읽지 못했어요. 스캔본이면 파일을 직접 올려 주세요.") from error
    elif content_type in {"text/html", "application/xhtml+xml"} or body.lstrip().startswith((b"<!doctype html", b"<html", b"<?xml")):
        parser = PageText()
        parser.feed(body.decode(charset, errors="replace"))
        title = " ".join(" ".join(parser.title_parts).split()) or urllib.parse.urlsplit(final_url).netloc
        text = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
    elif content_type.startswith("text/"):
        title = urllib.parse.urlsplit(final_url).path.rsplit("/", 1)[-1] or urllib.parse.urlsplit(final_url).netloc
        text = body.decode(charset, errors="replace")
    else:
        raise ValueError("웹페이지 또는 PDF 링크를 넣어 주세요. 이 형식은 지원하지 않아요.")
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if len(text) < 40:
        raise ValueError("읽을 수 있는 본문이 없어요. 로그인이 필요한 페이지거나 스캔 PDF일 수 있어요.")
    if len(text) > 120_000:
        text = text[:120_000] + "\n\n[긴 자료라 앞부분만 가져왔어요.]"
    return {"title": title[:240], "url": final_url, "text": text}
