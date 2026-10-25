"""Acquisition is separate from research; exact configured HTTPS URLs only."""
import re
import subprocess
from html.parser import HTMLParser
from urllib.parse import urlsplit
from .common import ROOT, PRIVATE, digest, now, read_json, write_json

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden: self.parts.append(value)

def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()

def html_text(raw):
    p = PlainText()
    p.feed(raw.decode('utf-8'))
    return normalized(' '.join(p.parts))

def allowed_url(url, configured):
    u = urlsplit(url)
    return (url in configured and u.scheme == 'https' and not u.username
            and not u.password and u.port in (None, 443)
            and u.hostname in ('psl.noaa.gov', 'www.sciencedirect.com', 'arxiv.org'))

def acquire(refresh=False):
    sources = read_json(ROOT / 'config/sources.json')
    allowed = {s['url'] for s in sources}
    current = PRIVATE / 'acquisition.json'
    if current.exists() and not refresh:
        manifest = read_json(current)
        for s in manifest:
            if digest((PRIVATE / s['raw_path']).read_bytes()) != s['sha256']:
                raise ValueError('Cached source hash mismatch: ' + s['id'])
            if s.get('text_path') and digest((PRIVATE / s['text_path']).read_bytes()) != s['text_sha256']:
                raise ValueError('Cached text hash mismatch: ' + s['id'])
        return manifest
    manifest = []
    for s in sources:
        if not allowed_url(s['url'], allowed) or not s['rights'].get('analyze'):
            raise ValueError('Source not approved')
        # No redirect following; no credentials; size/time/protocol bounded.
        try:
            p = subprocess.run(['curl', '--fail', '--silent', '--show-error', '--proto', '=https',
                            '--tlsv1.2', '--max-time', '45', '--max-filesize', '5000000',
                            '--retry', '2', '--retry-delay', '1', s['url']],
                               check=True, capture_output=True, timeout=150)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            if s.get('optional'):
                print('Optional full text unavailable:', s['id'], flush=True)
                continue
            raise
        raw = p.stdout
        if not raw or len(raw) > 5_000_000: raise ValueError('Source size invalid')
        h = digest(raw)
        path = PRIVATE / 'sources' / f"{s['id']}-{h}.{s['kind']}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        entry = dict(s, sha256=h, bytes=len(raw), retrieved_at=now(),
                     raw_path=str(path.relative_to(PRIVATE)), extraction_method='html.parser normalized whitespace v1')
        if s['kind'] == 'html':
            text = html_text(raw).encode()
            text_path = path.with_suffix('.txt')
            text_path.write_bytes(text)
            entry.update(text_path=str(text_path.relative_to(PRIVATE)), text_sha256=digest(text))
        manifest.append(entry)
        print('Acquired', s['id'], len(raw), 'bytes', flush=True)
    write_json(current, manifest)
    write_json(PRIVATE / 'acquisitions' / (digest(current.read_bytes()) + '.json'), manifest)
    return manifest

def evidence(source, quote, location):
    text = (PRIVATE / source['text_path']).read_text()
    start = text.find(normalized(quote))
    if start < 0: raise ValueError('Quotation not found in snapshot: ' + source['id'])
    return {'source_id': source['id'], 'source_hash': source['sha256'],
            'text_hash': source['text_sha256'], 'quote': normalized(quote),
            'start': start, 'end': start + len(normalized(quote)), 'location': location}

def validate_evidence(item, sources):
    s = sources[item['source_id']]
    text = (PRIVATE / s['text_path']).read_text()
    if digest((PRIVATE / s['raw_path']).read_bytes()) != item['source_hash']:
        raise ValueError('Source snapshot changed')
    if digest(text.encode()) != item['text_hash']:
        raise ValueError('Text snapshot changed')
    if text[item['start']:item['end']] != item['quote']:
        raise ValueError('Unsupported quotation')
