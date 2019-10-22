import airflow_queue_stats.calculate
import airflow_queue_stats.gather
from airflow.www.app import csrf
from flask import Blueprint, jsonify

blueprint = Blueprint("airflow_docker_stats", __name__)


@csrf.exempt
@blueprint.route("/queue/stats", methods=["GET"])
def get_stats():
    return jsonify(get_data())


def get_data():
    backlogged_queues = airflow_queue_stats.gather.get_backlog()
    workers = airflow_queue_stats.gather.get_workers()
    unfinished_task_instances = (
        airflow_queue_stats.gather.get_unfinished_task_instances()
    )
    dags = airflow_queue_stats.gather.get_dags()
    dag_runs = airflow_queue_stats.gather.get_dag_runs(
        task_instances=unfinished_task_instances
    )
    desired_usage = airflow_queue_stats.calculate.get_desired_usage(
        task_instances=unfinished_task_instances, dags=dags, dag_runs=dag_runs
    )
    queues = airflow_queue_stats.calculate.consolidate_queues(
        task_instances=unfinished_task_instances,
        backlogged_queues=backlogged_queues,
        workers=workers,
        desired_usage=desired_usage,
    )

    payload = {
        "data": {
            "queues": {},
            "workers": {},
            "totals": {
                "active": 0,
                "backlog": 0,
                "desired_usage": 0,
                "capacity": 0,
                "max_capacity": 0,
            },
        }
    }

    for queue in queues:
        queue_info = {
            "name": queue.name,
            "active": queue.active_count,
            "capacity": queue.capacity,
            "max_capacity": queue.max_capacity,
            "backlog": queue.backlog,
            "desired_usage": queue.desired_usage,
        }

        payload["data"]["queues"][queue.name] = queue_info

        payload["data"]["totals"]["active"] += queue.active_count
        payload["data"]["totals"]["backlog"] += queue.backlog
        payload["data"]["totals"]["desired_usage"] += queue.desired_usage
        payload["data"]["totals"]["capacity"] += queue.capacity
        payload["data"]["totals"]["max_capacity"] += queue.max_capacity

    for worker in workers:
        worker_info = {
            "name": worker.name,
            "active": worker.active_count,
            "capacity": worker.capacity,
            "max_capacity": worker.max_capacity,
            "queues": worker.queue_names,
        }

        payload["data"]["workers"][worker.name] = worker_info

    return payload
