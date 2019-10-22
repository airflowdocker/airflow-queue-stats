from airflow.plugins_manager import AirflowPlugin
from airflow_queue_stats.views import api


class QueueStatsPlugin(AirflowPlugin):
    name = "queue_stats"
    flask_blueprints = [api.blueprint]
