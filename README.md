# TheHive GraphView Dashboard

Servicio de recolección de métricas y visualización para TheHive, Cortex y Synapse.

## Características

- **Disponibilidad**: Monitoreo en tiempo real de Elasticsearch, Cassandra, TheHive, Cortex y Synapse.
- **Métricas SOC**: Casos creados/cerrados, MTTA, MTTR, SLA y Backlog.
- **CTI / MITRE**: Visualización de tácticas y técnicas MITRE ATT&CK detectadas en casos.
- **Correlación**: Estadísticas de clustering de campañas y propagación de TTPs.
- **Acceso Rápido**: Enlaces directos a las consolas de TheHive y Cortex.

## Componentes

1. **collector.py**: Script en Python que consulta la API de TheHive, calcula las métricas y las envía a un índice dedicado en Elasticsearch (`thehive_dashboard_metrics`).
2. **setup_grafana.py**: Script de aprovisionamiento que configura el datasource de Elasticsearch y crea el dashboard automáticamente en Grafana.
3. **dashboard.conf**: Archivo de configuración centralizada.

## Instalación y Uso

1. Asegúrate de que las credenciales en `dashboard.conf` sean correctas.
2. Instala el servicio de systemd:
   ```bash
   sudo cp /opt/TheHive-GraphView/misc/thehive-dashboard.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now thehive-dashboard
   ```
3. Configura Grafana (solo una vez):
   ```bash
   python3 setup_grafana.py
   ```
4. Accede al dashboard en `http://kirolsoar:3000`.

## Gestión del Servicio

- **Nombre del servicio**: `thehive-dashboard.service`
- Ver estado: `systemctl status thehive-dashboard`
- Ver logs: `journalctl -u thehive-dashboard -f`

## Consultas THQL (TheHive Query Language)

El colector utiliza el estándar THQL para filtrar casos de los últimos 30 días:
```json
{
    "_name": "filter",
    "_gt": {
        "_field": "_createdAt",
        "_value": <timestamp>
    }
}
```
