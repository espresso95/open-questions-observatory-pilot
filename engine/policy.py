"""Export gates run outside research code. No publication credentials here."""
import re
from pathlib import Path
from urllib.parse import urlsplit
from .common import canonical, digest

STATUSES = {
 'literature':{'unchecked','no_answer_found','partial_answer','addressed_in_literature','contested'},
 'feasibility':{'unassessed','needs_information','data_blocked','lab_dependent','compute_blocked','safety_blocked','pilot_ready'},
 'research':{'not_started','planned','running','completed','failed','inconclusive','stopped_budget'},
 'validation':{'unreviewed','automated_checks_passed','computationally_reproduced','human_reviewed','externally_reviewed'},
 'publication':{'private_draft','approved_for_disclosure','public_candidate','published','corrected','withdrawn'}
}

def validate_question(q):
    required = {'schema_version','id','title','scope','disciplines','source_evidence','statuses','literature_search','assessment','run_ids'}
    if required-set(q) or q['schema_version'] != '1.0' or not q['id'].startswith('Q-'):
        raise ValueError('Invalid question schema')
    if not q['source_evidence'] or q.get('demo'): raise ValueError('Unverified or demo question')
    for dimension,allowed in STATUSES.items():
        if q['statuses'].get(dimension) not in allowed: raise ValueError('Invalid status dimension')
    if q.get('resolved') and not (q.get('resolution_review') and
                                  q['resolution_review'].get('type') in ('human_scientific','external_scientific')):
        raise ValueError('Unreviewed scientific resolution')
    a = q['assessment']
    if a.get('dispatch_eligible') and (a.get('blockers') or any(v is None for v in a['ratings'].values())):
        raise ValueError('Hard gate or unknown input blocks dispatch')

def validate_sources(sources):
    for s in sources:
        if not s['rights'].get('analyze') or not s['rights'].get('export') or not s['rights'].get('license'):
            raise ValueError('Missing rights decision')
        if urlsplit(s['url']).scheme != 'https': raise ValueError('Unsafe source link')

def bundle_manifest(path, allow_repository_metadata=False):
    path = Path(path)
    entries = {}
    for p in sorted(path.rglob('*')):
        if p.is_symlink(): raise ValueError('Symlink prohibited in export')
        if not p.is_file() or p in (path/'manifest.json',path/'disclosure-approval.json'): continue
        rel = p.relative_to(path).as_posix()
        if any(part.startswith('.') for part in p.relative_to(path).parts):
            if not (allow_repository_metadata and p.relative_to(path).parts[0] in ('.github','.gitignore')):
                raise ValueError('Hidden export path')
        data = p.read_bytes()
        if len(data)>10*1024*1024: raise ValueError('Oversized artifact')
        if p.suffix in ('.json','.md','.py','.sh','.cff','.bib','.lock','.svg','.txt','.yml','.astro','.mjs','.ts','.css'):
            text = data.decode('utf-8')
            if re.search(r'(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----)',text):
                raise ValueError('Secret pattern detected')
        entries[rel] = digest(data)
    return {'schema_version':'1.0','files':entries,'sha256':digest(canonical(entries)),
            'publication_status':'private_draft','human_disclosure_approval':False}

def require_disclosure_approval(bundle, approval):
    current = bundle_manifest(bundle)
    if not approval or approval.get('approved_sha256') != current['sha256'] or not approval.get('human_approver'):
        raise ValueError('Human approval of exact current bundle is required before public disclosure')
    return current
