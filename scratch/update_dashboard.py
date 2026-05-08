import requests
import json
import configparser
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, 'conf', 'dashboard.conf'))

GRAFANA_URL = config.get('Grafana', 'url')
GRAFANA_USER = config.get('Grafana', 'user')
GRAFANA_PASS = config.get('Grafana', 'pass')

def update_dashboard(ds_uid):
    search_url = f"{GRAFANA_URL}/api/search?query=TheHive SOC & CTI Dashboard"
    auth = (GRAFANA_USER, GRAFANA_PASS)
    
    existing_uid = None
    search_resp = requests.get(search_url, auth=auth)
    if search_resp.status_code == 200:
        results = search_resp.json()
        for res in results:
            if res['title'] == "TheHive SOC & CTI Dashboard":
                existing_uid = res['uid']
                break

    url = f"{GRAFANA_URL}/api/dashboards/db"
    
    dashboard = {
        "dashboard": {
            "id": None,
            "uid": existing_uid,
            "title": "TheHive SOC & CTI Dashboard",
            "tags": ["thehive", "soc", "cti"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "Component Availability",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0},
                    "datasource": {"uid": ds_uid, "type": "elasticsearch"},
                    "targets": [
                        {"alias": "TheHive", "metrics": [{"id": "1", "type": "max", "field": "availability.thehive"}], "refId": "A"},
                        {"alias": "Cortex", "metrics": [{"id": "1", "type": "max", "field": "availability.cortex"}], "refId": "B"},
                        {"alias": "Synapse", "metrics": [{"id": "1", "type": "max", "field": "availability.synapse"}], "refId": "C"},
                        {"alias": "Elastic", "metrics": [{"id": "1", "type": "max", "field": "availability.elasticsearch"}], "refId": "D"},
                        {"alias": "Cassandra", "metrics": [{"id": "1", "type": "max", "field": "availability.cassandra"}], "refId": "E"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}],
                            "color": {"mode": "thresholds"}
                        }
                    }
                },
                {
                    "title": "SOC Operational Metrics",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.total_cases_30d"}], "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "none", "displayName": "Cases (30d)"}, "overrides": []},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "Mean Time To Resolve (MTTR)",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.mttr_hours"}], "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "h", "displayName": "MTTR"}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "Mean Time To Acknowledge (MTTA)",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.mtta_hours"}], "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "h", "displayName": "MTTA"}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "SLA Compliance",
                    "type": "gauge",
                    "gridPos": {"h": 4, "w": 6, "x": 18, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.sla_compliance_pct"}], "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100, "thresholds": {"mode": "absolute", "steps": [{"value": None, "color": "red"}, {"value": 80, "color": "yellow"}, {"value": 95, "color": "green"}]}}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "Top MITRE Tactics",
                    "type": "barchart",
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
                    "datasource": {"uid": ds_uid},
                    "targets": [
                        {
                            "bucketAggs": [
                                {
                                    "field": "metrics.top_tactics.name.keyword",
                                    "id": "2",
                                    "settings": {"min_doc_count": 1, "order": "desc", "orderBy": "1", "size": "10"},
                                    "type": "terms"
                                }
                            ],
                            "metrics": [{"id": "1", "type": "sum", "field": "metrics.top_tactics.count"}],
                            "query": "",
                            "refId": "A"
                        }
                    ]
                },
                {
                    "title": "Quick Access",
                    "type": "text",
                    "gridPos": {"h": 4, "w": 24, "x": 0, "y": 16},
                    "options": {
                        "content": "# [TheHive](http://kirolsoar:8000) | [Cortex](http://kirolsoar:8001)",
                        "mode": "markdown"
                    }
                }
            ],
            "schemaVersion": 36,
            "refresh": "5m"
        },
        "overwrite": True
    }
    
    resp = requests.post(url, auth=auth, json=dashboard)
    print(resp.text)

if __name__ == "__main__":
    update_dashboard("fflf20jyvklc0b")
