"""CI checks metadata and artifacts only. It never executes submitted research code."""
import json
import os
from pathlib import Path
from .common import ROOT,read_json,digest,canonical
from .policy import bundle_manifest,validate_question,validate_sources

def main():
    releases=read_json(ROOT/'publication/releases.json')['releases']
    expected=os.environ.get('EXPECTED_BUNDLE_SHA')
    if expected and expected not in {r['approved_bundle_sha256'] for r in releases}:
        raise SystemExit('Unapproved disclosure digest')
    protected=set()
    for release in releases:
        if not release.get('human_disclosure_approval'):raise SystemExit('Missing human disclosure approval')
        manifest=read_json(ROOT/release['approved_manifest'])
        if digest(canonical(manifest['files']))!=release['approved_bundle_sha256']:
            raise SystemExit('Archived approval manifest changed')
        for relative in release['immutable_paths']:
            p=ROOT/relative
            if not p.is_file() or p.is_symlink() or digest(p.read_bytes())!=manifest['files'][relative]:
                raise SystemExit('Changed approved scientific artifact: '+relative)
            protected.add(relative)
    # No new scientific file may silently bypass the disclosure registry.
    for directory in ('catalog','research','site/src/content','site/public/data','site/public/downloads','site/public/figures'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and p.relative_to(ROOT).as_posix() not in protected:
                raise SystemExit('Scientific file absent from approved release: '+str(p.relative_to(ROOT)))
    for p in (ROOT/'catalog/questions').rglob('question.json'):validate_question(read_json(p))
    for p in (ROOT/'catalog').glob('sources*.json'):validate_sources(read_json(p))
    for p in (ROOT/'research').glob('*/artifacts.sha256.json'):
        for relative,h in read_json(p).items():
            if digest((p.parent/relative).read_bytes())!=h:raise SystemExit('Research artifact mismatch')
    print('PASS: immutable approved science, disclosure registry, metadata, rights and research manifests. No research code executed.')

if __name__=='__main__':main()
