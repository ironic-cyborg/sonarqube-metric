import requests
import os
import datetime
import time

from influxdb_client import InfluxDBClient

class SonarApiClient:

    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd

    def _make_request(self, endpoint):
        r = requests.get(BASE_URL + endpoint, auth=(self.user, self.passwd))
        return r.json()

    def get_all_ids(self, endpoint):
        data = self._make_request(endpoint)
        ids = []
        for component in data['components']:
            dict = {
                'id': component['id'],
                'key': component['key']
            }
            ids.append(dict)
        return ids

    def get_all_available_metrics(self, endpoint):
        data = self._make_request(endpoint)
        metrics = []
        for metric in data['metrics']:
            if metric['type'] in ['RATING']: #['INT','MILLISEC','WORK_DUR','FLOAT','PERCENT','RATING']
                metrics.append(metric['key'])
        print ("metrics: ",metrics)
        return metrics

    def get_measures_by_component_id(self, endpoint):
        print ("Hitting: ",endpoint)
        data = self._make_request(endpoint)
        return data['component']['measures']


class Project:

    def __init__(self, identifier, key):
        self.id = identifier
        self.key = key
        self.metrics = None
        self.timestamp = datetime.datetime.utcnow().isoformat()

    def set_metrics(self, metrics):
        self.metrics = metrics

    def export_metrics(self):



        influx_client.write_api().write(INFLUX_BUCKET, INFLUX_ORG, self._prepare_metrics())

    def _prepare_metrics(self):
        json_to_export = []
        for metric in self.metrics:
            one_metric = {
                "measurement": metric['metric'],
                "tags": {
                    "id": self.id,
                    "key": self.key
                },
                "time": self.timestamp,
                "fields": {
                    "value": float(metric['value'] if ('value' in metric) else 0)
                }
            }
            json_to_export.append(one_metric)
        print ("###", json_to_export)
        return json_to_export

count=0
print ("before while loop...")
influx_client = InfluxDBClient(url=INFLUX_URL,
                               token=INFLUX_TOKEN,
                               org=INFLUX_ORG)
while True:
    count += 1
    print ("count -----")
    print (count)

#    nowtime = time.asctime( time.localtime(time.time()) )

    print ("begin export data...")

    # Fetch all projects IDs
    client = SonarApiClient(USER, PASSWORD)
    # ids = client.get_all_ids('/api/components/search?qualifiers=TRK')
    ids = client.get_all_ids('/api/projects/search')
    # Fetch all available metrics
    metrics = client.get_all_available_metrics('/api/metrics/search')
    comma_separated_metrics = ''
    for metric in metrics:
        comma_separated_metrics += metric + ','

    # Collect metrics per project
    uri = '/api/measures/component'
    for item in ids:
        project_id = item['id']
        project_key = item['key']
        print(project_key, project_id)
        project = Project(identifier=project_id, key=project_key)
        component_id_query_param = 'componentId=' + project_id
        metric_key_query_param = 'metricKeys=' + comma_separated_metrics
        measures = client.get_measures_by_component_id(uri + '?' + component_id_query_param + '&' + metric_key_query_param)
        project.set_metrics(measures)
        project.export_metrics()
        print("END")
    time.sleep(int(INTERVAL))
    break
