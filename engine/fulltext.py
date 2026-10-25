"""Obtain selected sources for private reading; short exported evidence is separately reviewed."""
import json
import re
import xml.etree.ElementTree as ET
from .common import PRIVATE,read_json,write_json,now,digest
from .retrieval import Broker
from .broker import html_text,normalized



def run():
    broker=Broker();papers=read_json(PRIVATE/'discovery/papers.json');results=[]
    directory=PRIVATE/'discovery/fulltext';directory.mkdir(parents=True,exist_ok=True)
    for identifier in read_json(PRIVATE/'discovery/fulltext-selection.json'):
        paper=next(p for p in papers if p['external_id']==identifier)
        output=directory/(paper['id']+'.txt')
        if output.exists():
            results.append(read_json(output.with_suffix('.json')));continue
        try:
            raw,snapshot=broker.fetch(paper['fulltext_url'],kind='fulltext',rights={
              'analyze':True,'export':'Short evidence and citation only; no full text redistribution',
              'license':paper.get('license') or 'Publicly readable source; redistribution not assumed'})
            if paper['provider']=='europepmc':
                xml=ET.fromstring(raw)
                text=normalized(' '.join(xml.itertext()))
                licenses=[normalized(' '.join(e.itertext())) for e in xml.findall('.//license')]
                snapshot['source_license_text']=licenses
            else:
                text=html_text(raw)
                if 'arXiv' not in text or len(text)<3000:raise ValueError('Not a complete article')
                license_match=re.search(r'License: (.{0,100})',text)
                snapshot['source_license_text']=license_match.group(1) if license_match else None
            output.write_text(text)
            record={'paper':paper,'snapshot':snapshot,'text_path':str(output.relative_to(PRIVATE)),
              'text_sha256':digest(text.encode()),'read_at':now(),'extraction':'normalized structured full text; equation rendering must be checked against source before formalization'}
            write_json(output.with_suffix('.json'),record);results.append(record)
            print(identifier,len(text),'full-text characters',flush=True)
        except Exception as e:
            results.append({'paper':paper,'outcome':'unavailable','error':str(e)})
            print(identifier,'unavailable:',str(e),flush=True)
    write_json(directory/'manifest.json',results)

if __name__=='__main__':run()
