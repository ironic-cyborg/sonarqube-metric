import requests
import os
import datetime
import time

from influxdb_client import InfluxDBClient

BASE_URL = os.getenv('SONAR_BASE_URL', 'http://172.30.102.24:30715')
USER = os.getenv('SONAR_USER', 'labellogic')
PASSWORD = os.getenv('SONAR_PASSWORD', 'labellogic@123')
INFLUX_URL = os.getenv('INFLUX_URL', 'http://localhost:8086')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET', 'new')
INFLUX_ORG = os.getenv('INFLUX_ORG', 'influxdata')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN', '2TQKkTL4k5CnXOoAt2dJq3UJtkJ3RUo9hY0N02Rqvu_RZXw0589xpY7pK8D40cCHKXZi_F6719pdWSfYP73d5A==')
INTERVAL = os.getenv('INTERVAL', '10')


class SonarApiClient:

    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd

    def _make_request(self, endpoint):
        r = requests.get(BASE_URL + endpoint, auth=(self.user, self.passwd))
        return r.json()

    def get_all_keys(self, endpoint):
        data = self._make_request(endpoint)
        print(data)
        keys = []
        for component in data['components']:
            dict = {
                'key': component['key']
            }
            keys.append(dict)
        return keys

    def get_all_available_metrics(self, endpoint):
        data = self._make_request(endpoint)
        metrics = []
        for metric in data['metrics']:
            if metric['type'] in ['INT','MILLISEC','FLOAT','PERCENT','RATING','WORK_DUR','STRING']:
                metrics.append(metric['key'])
                print(metric['key'] + " " + metric['type'])
        print ("metrics: ",metrics)
        return metrics

    def get_measures_by_component_key(self, endpoint):
        print ("Hitting: ",endpoint)
        data = self._make_request(endpoint)
        return data['component']['measures']
    
    def get_status_by_key(self, endpoint):
        print ("Checking the status: ",endpoint)
        data = self._make_request(endpoint)
        return data['projectStatus']['status']

    def get_users(self,endpoint):
        data = self._make_request(endpoint)
        return data
    
    def get_languages(self,endpoint):
        data = self._make_request(endpoint)
        return data


class Project:

    def __init__(self, key):
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
                    "key": self.key
                },
                "time": self.timestamp,
                "fields": {
                    "value": metric['value'] if ('value' in metric) else 0
                }
            }
            json_to_export.append(one_metric)
        print ("###", json_to_export)
        return json_to_export


class project_status:

    def __init__(self, key, status):
        self.key = key
        self.metric = 'project_status'
        self.timestamp = datetime.datetime.utcnow().isoformat()
        self.status = status


    def export_metric(self):
        influx_client.write_api().write(INFLUX_BUCKET, INFLUX_ORG, self._prepare_metric())

    def set_status(self, stat):
        self.status = stat   

    def _prepare_metric(self):
        json_to_exports = []
        for key in keys:
          if self.key == key['key']:  
            status_metric = {
                "measurement": self.metric,
                "tags": {
                    "key": self.key
                },
                "time": self.timestamp,
                "fields": {
                    "value": 1 if ( self.status == "OK") else 0
                }
            }
            json_to_exports.append(status_metric)
        print ("###", json_to_exports)
        return json_to_exports


    

count=0
print ("before while loop...")
influx_client = InfluxDBClient(url=INFLUX_URL,
                               token=INFLUX_TOKEN,
                               org=INFLUX_ORG)
print(influx_client.url)
while True:
    count += 1
    print ("count -----")
    print (count)

#    nowtime = time.asctime( time.localtime(time.time()) )

    print ("begin export data...")

    # Fetch all projects IDs
    client = SonarApiClient(USER, PASSWORD)
    keys = client.get_all_keys('/api/components/search?qualifiers=TRK')
    # ids = client.get_all_ids('/api/projects/search')
    # Fetch all available metrics
    metrics = client.get_all_available_metrics('/api/metrics/search')
    comma_separated_metrics = ''
    for metric in metrics:
        comma_separated_metrics += metric + ','

    # Collect metrics per project
    uri = '/api/measures/component'
    for item in keys:
        project_key = item['key']
        print(project_key)
        project = Project(key=project_key)
        component_query_param = 'component=' + project_key
        metric_key_query_param = 'metricKeys=' + comma_separated_metrics
        measures = client.get_measures_by_component_key(uri + '?' + component_query_param + '&' + metric_key_query_param)
        #measures = client.get_measures_by_component_key(uri + '?' + '0' +'&' +metric_key_query_param)
        project.set_metrics(measures)
        project.export_metrics()
        print("END")

    status_uri = '/api/qualitygates/project_status'
    for status_item in keys:
        project_key = status_item['key'] 
        print(project_key)
        project = project_status(key=project_key, status=0)
        status_query_param = '?projectKey=' + project_key
        status_value = client.get_status_by_key(status_uri + status_query_param)
        #print(status)
        project.set_status(stat=status_value)
        project.export_metric()
        print("END")     

    users_uri = '/api/users/search'
    user = client.get_users(users_uri)
    count = user['paging']['total']
    json_to_export = []
    for x in range(count):
        one_metric = {
                "measurement": 'users',
                "time": datetime.datetime.utcnow().isoformat(),
                "fields": {
                    "value": user['users'][x]['login']
                }
        }
        json_to_export.append(one_metric)
    print ("###", json_to_export)
    influx_client.write_api().write(INFLUX_BUCKET, INFLUX_ORG, json_to_export)


    languages_uri = '/api/languages/list'
    language = client.get_languages(languages_uri)
    json_to_export = []
    for y in language["languages"]:
        one_metric = {
                "measurement": 'languages',
                "time": datetime.datetime.utcnow().isoformat(),
                "fields": {
                    "value": y["key"],
                }
        }
        json_to_export.append(one_metric)
    print ("###", json_to_export)
    influx_client.write_api().write(INFLUX_BUCKET, INFLUX_ORG, json_to_export)
    time.sleep(int(INTERVAL))
    break