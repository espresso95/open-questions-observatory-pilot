"""Stage fixed saved predictions and observations; no calibration outcomes are inspected."""
import csv
import gzip
import io
import math
from .common import PRIVATE,now,digest,read_json,write_json
from .retrieval import Broker
from .archive import RemoteZip

BASE='lstm_ensemble_underdispersion_zenodo_folder/'

def run():
    directory=PRIVATE/'datasets/streamflow';directory.mkdir(parents=True,exist_ok=True)
    metadata=read_json(PRIVATE/'discovery/streamflow-zenodo-metadata.json')
    f=metadata['files'][0]
    rights={'analyze':True,'redistribute_derivatives':True,'license':'CC-BY-4.0',
      'attribution':'Justin Gallant and Tyler Wilson (2026), LSTM Ensemble Under-dispersion Code v1.1.0, doi:10.5281/zenodo.23142989'}
    archive=RemoteZip(Broker(),f['links']['self'],f['size'],rights)
    records=[]
    def member(name):
        path=directory/name.replace('/','-')
        if path.exists():
            record=read_json(path.with_suffix(path.suffix+'.json'))
            raw=path.read_bytes()
            if digest(raw)!=record['sha256']:raise ValueError('Staged member corruption')
        else:
            raw,record=archive.read(BASE+name);path.write_bytes(raw)
            write_json(path.with_suffix(path.suffix+'.json'),record)
        records.append(record);print('qualified input',name,len(raw),flush=True)
        return raw
    attrs=list(csv.DictReader(io.StringIO(member('data/processed/static_attributes.csv').decode())))
    print('attribute columns',list(attrs[0]),flush=True)
    names=[]
    for m in range(10):
        name=f'data/output/topographic_lstm/topographic_lstm_preds_member_{m}.csv'
        raw=member(name)
        if m==0:names=next(csv.reader(io.StringIO(raw.decode())))[1:];print('prediction columns',len(names),'first',names[:3],flush=True)
    member('data/processed/combined_streamflow.csv')
    write_json(directory/'acquisition.json',{'acquired_at':now(),'record_id':23142989,'rights':rights,
      'members':records,'range_snapshots':archive.snapshots,'selection':'Saved predictions, observations, attributes only; no serialized model/code execution',
      'archive_md5_verified':False})

if __name__=='__main__':run()
