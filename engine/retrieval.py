"""Shared broker: public HTTPS, bounded acquisition, immutable content-addressed cache."""
import ipaddress
import json
import re
import socket
import sqlite3
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from .common import ROOT,PRIVATE,digest,now,read_json,write_json

class RetrievalDenied(ValueError):pass
class QuotaExhausted(RuntimeError):pass
class ProviderUnavailable(RuntimeError):pass

class Broker:
    def __init__(self, root=None, policy=None):
        self.root=Path(root or PRIVATE/'broker');self.root.mkdir(parents=True,exist_ok=True)
        self.policy=policy or read_json(ROOT/'config/providers.json')
        self.db=sqlite3.connect(self.root/'state.sqlite3',timeout=20)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS snapshots(url TEXT,hash TEXT,path TEXT,record TEXT,PRIMARY KEY(url,hash));
          CREATE TABLE IF NOT EXISTS usage(day TEXT PRIMARY KEY,requests INTEGER NOT NULL DEFAULT 0,metadata INTEGER NOT NULL DEFAULT 0,fulltexts INTEGER NOT NULL DEFAULT 0,bytes INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,time TEXT,url TEXT,outcome TEXT,detail TEXT);
        ''')
        if 'reserved_bytes' not in {r[1] for r in self.db.execute('PRAGMA table_info(usage)')}:
            self.db.execute('ALTER TABLE usage ADD COLUMN reserved_bytes INTEGER NOT NULL DEFAULT 0');self.db.commit()

    def validate(self,url):
        try:u=urlsplit(url);port=u.port
        except ValueError as e:raise RetrievalDenied('Malformed URL') from e
        if u.scheme!='https' or u.hostname not in self.policy['allowed_hosts'] or port not in (None,443) or u.username or u.password or u.fragment:
            raise RetrievalDenied('Unapproved destination or credentials')
        try:addresses={x[4][0] for x in socket.getaddrinfo(u.hostname,443,type=socket.SOCK_STREAM)}
        except OSError as e:raise ProviderUnavailable('DNS lookup failed') from e
        if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses):
            raise RetrievalDenied('Non-public destination')
        # Pin the validated IPv4 address for curl; no DNS rebinding during the call.
        ip=next((x for x in sorted(addresses) if ':' not in x),next(iter(addresses)))
        return u.hostname,ip

    def reserve(self,kind,items):
        day=now()[:10];limits=self.policy['budgets']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.db.execute('INSERT OR IGNORE INTO usage(day) VALUES(?)',(day,))
            row=self.db.execute('SELECT requests,metadata,fulltexts,bytes,reserved_bytes FROM usage WHERE day=?',(day,)).fetchone()
            available=limits['bytes_per_day']-row[3]-row[4]
            if row[0]>=limits['requests_per_day'] or available<=0 or (kind=='metadata' and row[1]+items>limits['metadata_items_per_day']) or (kind=='fulltext' and row[2]+1>limits['fulltexts_per_day']):
                raise QuotaExhausted('Daily acquisition budget exhausted; no paid fallback')
            capacity=min(available,limits['max_response_bytes'])
            self.db.execute('UPDATE usage SET requests=requests+1,metadata=metadata+?,fulltexts=fulltexts+?,reserved_bytes=reserved_bytes+? WHERE day=?',(items if kind=='metadata' else 0,1 if kind=='fulltext' else 0,capacity,day))
            self.db.commit()
            return day,capacity
        except Exception:self.db.rollback();raise

    def event(self,url,outcome,detail):
        self.db.execute('INSERT INTO events(time,url,outcome,detail) VALUES(?,?,?,?)',(now(),url,outcome,detail));self.db.commit()

    def fetch(self,url,kind='metadata',items=1,rights=None,refresh=False):
        if not rights or not rights.get('analyze'):raise RetrievalDenied('Missing analysis-rights decision')
        if not refresh:
            row=self.db.execute('SELECT path,record FROM snapshots WHERE url=? ORDER BY rowid DESC LIMIT 1',(url,)).fetchone()
            if row:
                record=json.loads(row[1]);data=(self.root/row[0]).read_bytes()
                if digest(data)!=record['sha256']:raise ValueError('Cached snapshot integrity failure')
                return data,record
        original=url
        for redirect in range(3):
            host,ip=self.validate(url)
            day,capacity=self.reserve(kind,items)
            token=digest((url+now()).encode())[:20]
            headers=self.root/(token+'.headers')
            observed_bytes=0
            try:
                p=subprocess.run(['curl','--disable','--silent','--show-error','--proto','=https','--tlsv1.2',
                  '--max-time',str(self.policy['budgets']['request_seconds']),
                  '--max-filesize',str(capacity),
                  '--resolve',host+':443:'+('['+ip+']' if ':' in ip else ip),
                  '--dump-header',str(headers),'--user-agent','OpenQuestionsObservatory/0.2 research-pilot',url],capture_output=True,timeout=50)
                observed_bytes=len(p.stdout)
                if p.returncode:raise ProviderUnavailable('Bounded request failed: '+str(p.returncode))
                raw_headers=headers.read_text(errors='replace');statuses=re.findall(r'^HTTP/\S+\s+(\d+)',raw_headers,re.M)
                if not statuses:raise ProviderUnavailable('Missing HTTP response status')
                status=int(statuses[-1]);fields={k.lower():v.strip() for k,v in re.findall(r'^([^\s:]+):\s*(.*?)\r?$',raw_headers,re.M)}
                if status in (301,302,303,307,308):
                    url=urljoin(url,fields.get('location',''))
                    if redirect==2:raise ProviderUnavailable('Redirect limit exceeded')
                    continue
                if status!=200:
                    self.event(original,'http_error',str(status))
                    raise ProviderUnavailable(f'HTTP {status}; not an empty scientific search')
                data=p.stdout
                if not data or len(data)>capacity:raise ProviderUnavailable('Invalid response size')
                h=digest(data);path=self.root/'objects'/h
                path.parent.mkdir(exist_ok=True);path.write_bytes(data)
                record={'url':original,'final_url':url,'sha256':h,'retrieved_at':now(),'bytes':len(data),
                  'content_type':fields.get('content-type'),'etag':fields.get('etag'),'last_modified':fields.get('last-modified'),
                  'kind':kind,'rights':rights,'path':str(path.relative_to(self.root))}
                self.db.execute('INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?)',(original,h,record['path'],json.dumps(record,sort_keys=True)))
                self.db.commit()
                self.event(original,'success',h)
                return data,record
            finally:
                self.db.execute('UPDATE usage SET reserved_bytes=reserved_bytes-?,bytes=bytes+? WHERE day=?',(capacity,observed_bytes,day));self.db.commit()
                headers.unlink(missing_ok=True)
        raise ProviderUnavailable('No valid response')
