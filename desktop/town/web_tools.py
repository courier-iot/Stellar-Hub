"""Internet Café tools: Wikipedia, DuckDuckGo results, and reading a page as plain text."""
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
from html import unescape
from html.parser import HTMLParser

UA = "AITown/0.2 (personal hobby project; local AI resident)"


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(2_000_000)
        charset = r.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def wiki_search(query, n=3):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n})
    data = json.loads(_get(url))
    return [h["title"] for h in data.get("query", {}).get("search", [])]


def wiki_extract(title, max_chars=3500):
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "extracts", "explaintext": 1, "exintro": 1,
         "titles": title, "format": "json", "redirects": 1})
    pages = json.loads(_get(url)).get("query", {}).get("pages", {})
    for p in pages.values():
        return (p.get("extract") or "")[:max_chars]
    return ""


def ddg_search(query, n=5):
    html = _get("https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query}))
    results = []
    for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
        href, title = m.group(1), re.sub("<.*?>", "", m.group(2))
        if "uddg=" in href:
            href = urllib.parse.unquote(urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("uddg", [href])[0])
        if href.startswith("//"):
            href = "https:" + href
        if "duckduckgo.com/y.js" in href:  # ads
            continue
        results.append({"title": unescape(title).strip(), "url": href})
        if len(results) >= n:
            break
    return results


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form"}

    def __init__(self):
        super().__init__()
        self.out, self.depth = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth += 1
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "tr"):
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.out.append(data)


def _public_url(url):
    """True only for http(s) links to public internet addresses. Blocks localhost, your home network,
    Tailscale addresses and so on, so a web page can't trick the resident into poking at your devices."""
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        return False
    try:
        infos = socket.getaddrinfo(u.hostname, u.port or (443 if u.scheme == "https" else 80))
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
                or ip.is_unspecified or ip in ipaddress.ip_network("100.64.0.0/10")):
            return False
    return True


class _SafeRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _public_url(newurl):
            raise ValueError("That page redirects somewhere private, so I won't follow it.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_SAFE_OPENER = urllib.request.build_opener(_SafeRedirects)


def read_page(url, max_chars=7000):
    if not _public_url(url):
        raise ValueError("I can only open public web pages.")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with _SAFE_OPENER.open(req, timeout=20) as r:
        ctype = r.headers.get("Content-Type", "")
        if ctype and not any(t in ctype for t in ("text/", "html", "xml", "json")):
            raise ValueError("That link isn't a web page.")
        raw = r.read(2_000_000)
        html = raw.decode(r.headers.get_content_charset() or "utf-8", errors="replace")
    p = _Text()
    p.feed(html)
    text = re.sub(r"[ \t]+", " ", "".join(p.out))
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    return text[:max_chars]
