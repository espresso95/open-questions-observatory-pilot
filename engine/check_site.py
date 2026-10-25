"""Check the built static site, including all same-origin links and export boundaries."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .common import ROOT,read_json,write_json,now

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ('href','src') and value:self.links.append(value)

def main():
    site=ROOT/'site/dist';checked=0
    for p in site.rglob('*.html'):
        text=p.read_text();links=Links();links.feed(text)
        assert '<html lang="en"' in text and '<main id="main"' in text
        if p.relative_to(site).parts[0]=='research':
            assert 'no external scientific review' in text.lower()
        assert '.private/' not in text and '/Users/mottbot/' not in text
        for url in links.links:
            parsed=urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:continue
            path=unquote(parsed.path)
            target=site/path.lstrip('/') if path.startswith('/') else p.parent/path
            assert target.exists(),f'Broken link {url} in {p.relative_to(site)}'
            if target.is_dir():assert (target/'index.html').is_file(),str(target)
            checked+=1
    assert (site/'pagefind/pagefind.js').exists()
    assert not list(site.rglob('*.sqlite3')) and not list(site.rglob('*.data'))
    manifest=read_json(site/'data/v1/manifest.json')
    assert manifest['human_disclosure_approval'] is False and manifest['record_count']==1
    result={'checked_at':now(),'html_pages':len(list(site.rglob('*.html'))),'local_links_checked':checked,
            'broken_links':0,'private_state_absent':True,'pagefind_bundle_present':True}
    write_json(ROOT/'output/static-site-checks.json',result)
    print(result)

if __name__=='__main__':main()
