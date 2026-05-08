import requests
import json
import logging

import configparser
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, 'conf', 'dashboard.conf'))

GRAFANA_URL = config.get('Grafana', 'url')
GRAFANA_USER = config.get('Grafana', 'user')
GRAFANA_PASS = config.get('Grafana', 'pass')
ES_URL = config.get('Elasticsearch', 'url')
ES_USER = config.get('Elasticsearch', 'user')
ES_PASS = config.get('Elasticsearch', 'pass')
ES_INDEX = config.get('Elasticsearch', 'index')

FIXED_UID = "thehive-metrics-ds"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_datasource():
    logger.info("Setting up Elasticsearch datasource in Grafana...")
    url = f"{GRAFANA_URL}/api/datasources"
    auth = (GRAFANA_USER, GRAFANA_PASS)
    
    resp = requests.get(url, auth=auth)
    ds_id = None
    for ds in resp.json():
        if ds['name'] == 'TheHive-Metrics' or ds['uid'] == FIXED_UID:
            ds_id = ds['id']
            # Update via PUT if possible, or delete/recreate
            requests.delete(f"{url}/{ds_id}", auth=auth)
            break

    payload = {
        "name": "TheHive-Metrics",
        "uid": FIXED_UID,
        "type": "elasticsearch",
        "url": ES_URL,
        "access": "proxy",
        "basicAuth": True,
        "basicAuthUser": ES_USER,
        "secureJsonData": {
            "basicAuthPassword": ES_PASS
        },
        "jsonData": {
            "index": ES_INDEX,
            "timeField": "@timestamp",
            "esVersion": "7.17.0",
            "maxConcurrentShardRequests": 5
        }
    }
    
    resp = requests.post(url, auth=auth, json=payload)
    if resp.status_code == 200:
        return FIXED_UID
    return FIXED_UID # Return anyway if it failed because it exists

def setup_dashboard(ds_uid):
    logger.info("Setting up Dashboard in Grafana...")
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
                # Availability Row
                {
                    "title": "Component Availability",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 24, "x": 0, "y": 0},
                    "datasource": {"uid": ds_uid, "type": "elasticsearch"},
                    "targets": [
                        {"alias": "TheHive", "metrics": [{"id": "1", "type": "max", "field": "availability.thehive"}], "query": "metric_type:\"summary\"", "refId": "A"},
                        {"alias": "Cortex", "metrics": [{"id": "1", "type": "max", "field": "availability.cortex"}], "query": "metric_type:\"summary\"", "refId": "B"},
                        {"alias": "Synapse", "metrics": [{"id": "1", "type": "max", "field": "availability.synapse"}], "query": "metric_type:\"summary\"", "refId": "C"},
                        {"alias": "Elastic", "metrics": [{"id": "1", "type": "max", "field": "availability.elasticsearch"}], "query": "metric_type:\"summary\"", "refId": "D"},
                        {"alias": "Cassandra", "metrics": [{"id": "1", "type": "max", "field": "availability.cassandra"}], "query": "metric_type:\"summary\"", "refId": "E"}
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "mappings": [{"type": "value", "options": {"0": {"text": "DOWN", "color": "red"}, "1": {"text": "UP", "color": "green"}}}],
                            "color": {"mode": "thresholds"}
                        }
                    },
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                # SOC Metrics Row
                {
                    "title": "Cases (30d)",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 0, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.total_cases_30d"}], "query": "metric_type:\"summary\"", "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "none"}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "MTTR",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 6, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.mttr_hours"}], "query": "metric_type:\"summary\"", "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "h"}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "MTTA",
                    "type": "stat",
                    "gridPos": {"h": 4, "w": 6, "x": 12, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.mtta_hours"}], "query": "metric_type:\"summary\"", "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "h"}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                {
                    "title": "SLA Compliance",
                    "type": "gauge",
                    "gridPos": {"h": 4, "w": 6, "x": 18, "y": 4},
                    "datasource": {"uid": ds_uid},
                    "targets": [{"metrics": [{"id": "1", "type": "max", "field": "metrics.sla_compliance_pct"}], "query": "metric_type:\"summary\"", "refId": "A"}],
                    "fieldConfig": {"defaults": {"unit": "percent", "min": 0, "max": 100, "thresholds": {"mode": "absolute", "steps": [{"value": None, "color": "red"}, {"value": 80, "color": "yellow"}, {"value": 95, "color": "green"}]}}},
                    "options": {"reduceOptions": {"values": False, "calcs": ["lastNotNull"]}}
                },
                # MITRE Row
                {
                    "title": "Top MITRE Tactics",
                    "type": "barchart",
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8},
                    "datasource": {"uid": ds_uid},
                    "targets": [
                        {
                            "bucketAggs": [
                                {
                                    "field": "tactic_name.keyword",
                                    "id": "2",
                                    "settings": {"min_doc_count": 1, "order": "desc", "orderBy": "1", "size": "10"},
                                    "type": "terms"
                                }
                            ],
                            "metrics": [{"id": "1", "type": "max", "field": "count"}],
                            "query": "metric_type:\"tactic\"",
                            "refId": "A"
                        }
                    ]
                },
                {
                    "title": "Top MITRE Techniques",
                    "type": "barchart",
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8},
                    "datasource": {"uid": ds_uid},
                    "targets": [
                        {
                            "bucketAggs": [
                                {
                                    "field": "technique_name.keyword",
                                    "id": "2",
                                    "settings": {"min_doc_count": 1, "order": "desc", "orderBy": "1", "size": "10"},
                                    "type": "terms"
                                }
                            ],
                            "metrics": [{"id": "1", "type": "max", "field": "count"}],
                            "query": "metric_type:\"technique\"",
                            "refId": "A"
                        }
                    ]
                },
                # Quick Links
                {
                    "title": "Quick Access",
                    "type": "text",
                    "gridPos": {"h": 4, "w": 24, "x": 0, "y": 16},
                    "options": {
                        "content": "# [TheHive]([thehive-url]) | [Cortex]([cortex-url])",
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
    if resp.status_code == 200:
        logger.info("Dashboard created successfully.")
    else:
        logger.error(f"Failed to create dashboard: {resp.text}")

if __name__ == "__main__":
    ds_uid = setup_datasource()
    if ds_uid:
        setup_dashboard(ds_uid)

#Test
