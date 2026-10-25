"""Prepare a reviewable, allowlisted GitHub publication candidate. No network writes."""
import shutil
from .common import ROOT,PRIVATE,write_json
from .policy import bundle_manifest

def main():
    target=PRIVATE/'publication-candidate'
    if target.exists():shutil.rmtree(target)
    target.mkdir()
    for name in ['README.md','.gitignore','engine','config','schemas','policies','tests','.github']:
        src=ROOT/name;dst=target/name
        if src.is_dir():shutil.copytree(src,dst,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        else:shutil.copy2(src,dst)
    shutil.copytree(ROOT/'site',target/'site',ignore=shutil.ignore_patterns('node_modules','dist','.astro'))
    for name in ['catalog','research']:shutil.copytree(ROOT/'review-bundle'/name,target/name)
    manifest=bundle_manifest(target,allow_repository_metadata=True)
    write_json(target/'manifest.json',manifest)
    write_json(PRIVATE/'publication-review.json',{'directory':str(target),'sha256':manifest['sha256'],
                                               'human_approval':False,'contains':'Code, static site sources, question record, research artifacts and approved public NOAA data; no private cache, database or design document'})
    print('Publication candidate:',manifest['sha256'])

if __name__=='__main__':main()
