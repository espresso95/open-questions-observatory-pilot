"""CI checks metadata and artifacts only. It never executes submitted research code."""
import json
import os
from pathlib import Path
from .common import ROOT,read_json,digest
from .policy import bundle_manifest,validate_question,validate_sources

def main():
    manifest=read_json(ROOT/'manifest.json')
    expected=os.environ.get('EXPECTED_BUNDLE_SHA',manifest['sha256'])
    if expected!=manifest['sha256']:raise SystemExit('Unapproved disclosure digest')
    # Check only the approved file list: CI generated files (node_modules/dist) are not inputs.
    for relative,h in manifest['files'].items():
        p=ROOT/relative
        if not p.is_file() or p.is_symlink() or digest(p.read_bytes())!=h:raise SystemExit('Changed approved artifact: '+relative)
    for p in (ROOT/'catalog/questions').rglob('question.json'):validate_question(read_json(p))
    validate_sources(read_json(ROOT/'catalog/sources.json'))
    for p in (ROOT/'research').glob('*/artifacts.sha256.json'):
        for relative,h in read_json(p).items():
            if digest((p.parent/relative).read_bytes())!=h:raise SystemExit('Research artifact mismatch')
    print('PASS: approved hashes, metadata, rights and research manifests. No research code executed.')

if __name__=='__main__':main()
