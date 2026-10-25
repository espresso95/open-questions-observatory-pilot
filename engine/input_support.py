"""Prospective predictor-support gates. These never inspect evaluation errors."""
import csv
import gzip
from collections import Counter
from .adapters.streamflow import quantile

def streamflow(path,parameters):
    calibration=[];evaluation=[]
    with gzip.open(path,'rt',newline='') as f:
        for row in csv.DictReader(f):
            group,date=row['calibration_group'],row['date']
            if group=='calibration' and date<=parameters['calibration_end']:
                calibration.append(float(row['mean_mm_day']))
            elif group=='evaluation' and parameters['evaluation_start']<=date<=parameters['evaluation_end']:
                evaluation.append((row['station'],float(row['mean_mm_day'])))
    threshold=quantile(calibration,parameters['flow_bin_edges'][-1])
    counts=Counter(station for station,mean in evaluation if mean>=threshold)
    eligible=sum(n>=parameters['minimum_high_rows_per_station'] for n in counts.values())
    return {'qualified':eligible>=parameters['minimum_evaluation_stations'],'eligible_stations':eligible,
      'required_stations':parameters['minimum_evaluation_stations'],'high_flow_threshold':threshold,
      'uses_evaluation_errors':False,'meaning':'Support conditional on existing observation availability; no performance result examined'}
