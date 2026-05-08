import requests
import json
import time
import datetime
from requests.auth import HTTPBasicAuth
import logging
import socket

import configparser
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, 'conf', 'dashboard.conf'))

THEHIVE_URL = config.get('TheHive', 'url')
THEHIVE_API_KEY = config.get('TheHive', 'api_key')
ES_URL = config.get('Elasticsearch', 'url')
ES_USER = config.get('Elasticsearch', 'user')
ES_PASS = config.get('Elasticsearch', 'pass')
ES_INDEX = config.get('Elasticsearch', 'index')

CORTEX_URL = config.get('Components', 'cortex_url')
SYNAPSE_URL = config.get('Components', 'synapse_url')
ELASTIC_URL = ES_URL
CASSANDRA_HOST = config.get('Components', 'cassandra_host')
CASSANDRA_PORT = config.getint('Components', 'cassandra_port')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_http_availability(url, name):
    try:
        response = requests.get(url, timeout=5, verify=False)
        return 1 if response.status_code < 500 else 0
    except Exception as e:
        logger.debug(f"Availability check failed for {name}: {e}")
        return 0

def check_tcp_availability(host, port, name):
    try:
        with socket.create_connection((host, port), timeout=5):
            return 1
    except Exception as e:
        logger.debug(f"Availability check failed for {name}: {e}")
        return 0

def get_thehive_metrics():
    headers = {"Authorization": f"Bearer {THEHIVE_API_KEY}"}
    metrics = {
        "total_cases_30d": 0,
        "closed_cases_30d": 0,
        "open_cases": 0,
        "mttr_hours": 0,
        "mtta_hours": 0,
        "sla_compliance_pct": 0,
        "backlog": 0,
        "top_tactics": [],
        "top_techniques": [],
        "technique_reuse_rate": 0,
        "campaign_clustering_count": 0,
        "avg_alerts_per_cluster": 0
    }
    
    try:
        now = int(time.time() * 1000)
        thirty_days_ago = now - (30 * 24 * 60 * 60 * 1000)
        
        # Query cases from the last 30 days
        query = {
            "query": [
                {"_name": "listCase"},
                {"_name": "filter", "_gt": {"_field": "_createdAt", "_value": thirty_days_ago}}
            ]
        }
        
        response = requests.post(f"{THEHIVE_URL}/api/v1/query", headers=headers, json=query)
        if response.status_code != 200:
            logger.error(f"TheHive API query failed: {response.text}")
            return metrics
            
        cases = response.json()
        if not isinstance(cases, list):
            return metrics

        metrics['total_cases_30d'] = len(cases)
        metrics['closed_cases_30d'] = len([c for c in cases if c.get('status') == 'Resolved'])
        metrics['open_cases'] = len([c for c in cases if c.get('status') == 'Open'])
        metrics['backlog'] = metrics['open_cases']
        
        resolved_times = []
        ack_times = []
        sla_compliant = 0
        total_for_sla = 0
        
        all_ttps = []
        alerts_per_case = []

        for case in cases:
            # MTTR
            if case.get('status') == 'Resolved' and case.get('endDate'):
                resolved_times.append(case['endDate'] - case['_createdAt'])
            
            # MTTA
            ack_date = case.get('inProgressDate') or case.get('startDate')
            if ack_date:
                ack_times.append(ack_date - case['_createdAt'])
            
            # SLA
            severity = case.get('severity', 2)
            limit = 24 * 3600 * 1000 if severity >= 3 else 48 * 3600 * 1000
            if case.get('status') == 'Resolved' and case.get('endDate'):
                total_for_sla += 1
                if (case['endDate'] - case['_createdAt']) <= limit:
                    sla_compliant += 1
            elif case.get('status') == 'Open':
                total_for_sla += 1
                if (now - case['_createdAt']) <= limit:
                    sla_compliant += 1

            # TTPs
            case_id = case.get('_id')
            if case_id:
                ttp_resp = requests.get(f"{THEHIVE_URL}/api/v1/pattern/case/{case_id}", headers=headers)
                if ttp_resp.status_code == 200:
                    ttps = ttp_resp.json()
                    if isinstance(ttps, list):
                        all_ttps.extend(ttps)
            
            # Correlation / Clustering
            alert_query = {
                "query": [
                    {"_name": "listAlert"},
                    {"_name": "filter", "_eq": {"_field": "case", "_value": case_id}}
                ]
            }
            alert_resp = requests.post(f"{THEHIVE_URL}/api/v1/query", headers=headers, json=alert_query)
            if alert_resp.status_code == 200:
                alert_count = len(alert_resp.json())
                if alert_count > 1:
                    alerts_per_case.append(alert_count)

        if resolved_times:
            metrics['mttr_hours'] = round(sum(resolved_times) / len(resolved_times) / (1000 * 60 * 60), 2)
        if ack_times:
            metrics['mtta_hours'] = round(sum(ack_times) / len(ack_times) / (1000 * 60 * 60), 2)
        if total_for_sla:
            metrics['sla_compliance_pct'] = round((sla_compliant / total_for_sla) * 100, 2)

        # MITRE Processing
        tactic_counts = {}
        technique_counts = {}
        for ttp in all_ttps:
            for tactic in ttp.get('tactics', []):
                norm_tactic = tactic.replace('-', ' ').title()
                tactic_counts[norm_tactic] = tactic_counts.get(norm_tactic, 0) + 1
            
            tech_id = ttp.get('patternId')
            if tech_id:
                technique_counts[tech_id] = technique_counts.get(tech_id, 0) + 1
        
        metrics['top_tactics'] = [{"name": k, "count": v} for k, v in sorted(tactic_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
        metrics['top_techniques'] = [{"name": k, "count": v} for k, v in sorted(technique_counts.items(), key=lambda x: x[1], reverse=True)[:10]]
        
        if len(technique_counts) > 0:
            total_uses = sum(technique_counts.values())
            unique_techs = len(technique_counts)
            metrics['technique_reuse_rate'] = round(total_uses / unique_techs, 2)

        metrics['campaign_clustering_count'] = len(alerts_per_case)
        if alerts_per_case:
            metrics['avg_alerts_per_cluster'] = round(sum(alerts_per_case) / len(alerts_per_case), 2)

    except Exception as e:
        logger.error(f"Error fetching TheHive metrics: {e}")
        
    return metrics

def push_to_es(metrics):
    try:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
        auth = HTTPBasicAuth(ES_USER, ES_PASS)
        
        # 1. Push Summary document
        summary_data = {
            "@timestamp": timestamp,
            "metric_type": "summary",
            "availability": {
                "thehive": check_http_availability(THEHIVE_URL, "TheHive"),
                "cortex": check_http_availability(CORTEX_URL, "Cortex"),
                "synapse": check_http_availability(f"{SYNAPSE_URL}/version", "Synapse"),
                "elasticsearch": check_http_availability(ELASTIC_URL, "Elasticsearch"),
                "cassandra": check_tcp_availability(CASSANDRA_HOST, CASSANDRA_PORT, "Cassandra")
            },
            "metrics": {k: v for k, v in metrics.items() if k not in ['top_tactics', 'top_techniques']}
        }
        
        requests.post(f"{ES_URL}/{ES_INDEX}/_doc", auth=auth, json=summary_data)
        
        # 2. Push Tactic documents (individual for easier aggregation)
        for t in metrics.get('top_tactics', []):
            tactic_data = {
                "@timestamp": timestamp,
                "metric_type": "tactic",
                "tactic_name": t['name'],
                "count": t['count']
            }
            requests.post(f"{ES_URL}/{ES_INDEX}/_doc", auth=auth, json=tactic_data)

        # 3. Push Technique documents
        for t in metrics.get('top_techniques', []):
            tech_data = {
                "@timestamp": timestamp,
                "metric_type": "technique",
                "technique_name": t['name'],
                "count": t['count']
            }
            requests.post(f"{ES_URL}/{ES_INDEX}/_doc", auth=auth, json=tech_data)

        logger.info("Metrics pushed to ES successfully (granularly)")
            
    except Exception as e:
        logger.error(f"Error pushing to ES: {e}")

if __name__ == "__main__":
    logger.info("Starting collector...")
    # Create index if not exists
    requests.put(f"{ES_URL}/{ES_INDEX}", auth=HTTPBasicAuth(ES_USER, ES_PASS))
    
    while True:
        hive_metrics = get_thehive_metrics()
        push_to_es(hive_metrics)
        time.sleep(300) # Run every 5 minutes
