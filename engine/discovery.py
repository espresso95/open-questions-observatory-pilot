"""Budgeted scholarly metadata discovery; admission requires separate full-text review."""
import argparse
import json
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from .common import ROOT,PRIVATE,read_json,write_json,now,digest
from .retrieval import Broker,ProviderUnavailable
from .broker import html_text,normalized

METADATA_RIGHTS={'analyze':True,'export':'bibliographic_metadata_and_short_evidence_only','license':'Provider bibliographic response; full-text rights assessed separately'}

def arxiv(raw,discipline):
    root=ET.fromstring(raw);ns={'a':'http://www.w3.org/2005/Atom'}
    result=[]
    for e in root.findall('a:entry',ns):
        get=lambda name:normalized(e.findtext('a:'+name,default='',namespaces=ns))
        url=get('id');identifier=url.rsplit('/',1)[-1]
        result.append({'id':'P-'+identifier.replace('.','-'),'provider':'arxiv','external_id':identifier,
          'discipline':discipline,'title':get('title'),'abstract':get('summary'),'published':get('published'),
          'updated':get('updated'),'url':url.replace('http://','https://'),'fulltext_url':'https://arxiv.org/html/'+identifier,
          'authors':[normalized(a.findtext('a:name',default='',namespaces=ns)) for a in e.findall('a:author',ns)],
          'screening_level':'abstract_metadata','admission_status':'not_assessed'})
    return result

def europepmc(raw,discipline):
    result=[]
    for e in json.loads(raw)['resultList']['result']:
        abstract=e.get('abstractText','')
        if '<' in abstract:abstract=html_text(abstract.encode())
        pmcid=e.get('pmcid')
        result.append({'id':'P-'+(pmcid or e['id']),'provider':'europepmc','external_id':pmcid or e['id'],
          'discipline':discipline,'title':e['title'],'abstract':normalized(abstract),'published':e.get('firstPublicationDate'),
          'updated':None,'url':'https://europepmc.org/article/'+('PMC/'+pmcid if pmcid else e.get('source','MED')+'/'+e['id']),
          'fulltext_url':'https://www.ebi.ac.uk/europepmc/webservices/rest/'+pmcid+'/fullTextXML' if pmcid else None,
          'authors':e.get('authorString',''),'doi':e.get('doi'),'license':e.get('license'),
          'screening_level':'abstract_metadata','admission_status':'not_assessed'})
    return result

def run():
    config=read_json(ROOT/'config/discovery.json');broker=Broker();records=[];searches=[]
    count=config['papers_per_discipline']
    for stream in config['streams']:
        if stream['provider']=='arxiv':
            url='https://export.arxiv.org/api/query?'+urlencode({'search_query':stream['query'],'start':0,'max_results':count,'sortBy':'submittedDate','sortOrder':'descending'})
            parse=arxiv
        else:
            url='https://www.ebi.ac.uk/europepmc/webservices/rest/search?'+urlencode({'query':stream['query'],'format':'json','resultType':'core','pageSize':count,'sort':'FIRST_PDATE_D desc'})
            parse=europepmc
        try:
            raw,snapshot=broker.fetch(url,kind='metadata',items=count,rights=METADATA_RIGHTS)
            items=parse(raw,stream['discipline']);records.extend(items)
            searches.append(dict(stream,url=url,snapshot=snapshot,result_count=len(items),outcome='success'))
            print(stream['discipline'],len(items),'metadata records',flush=True)
        except Exception as e:
            searches.append(dict(stream,url=url,outcome='failed',error=str(e)))
            print(stream['discipline'],'deferred:',str(e),flush=True)
    unique={r['external_id']:r for r in records}
    destination=PRIVATE/'discovery';destination.mkdir(exist_ok=True)
    write_json(destination/'papers.json',list(unique.values()))
    write_json(destination/'searches.json',{'queried_at':now(),'cutoff':config['cutoff'],'searches':searches,
      'coverage':'Bibliographic abstracts only at this stage. No missing full text is treated as read. No answer/open classification is inferred from abstract keywords.'})
    lines=[]
    for r in unique.values():
        lines.append(f"## {r['id']} | {r['discipline']}\n{r['title']}\n{r['url']}\n{r['abstract']}\n")
    (destination/'screening.txt').write_text('\n'.join(lines))
    print('Total unique abstracts:',len(unique),flush=True)

if __name__=='__main__':run()
