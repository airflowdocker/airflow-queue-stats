from airflow.executors.celery_executor import app as celery_app
from airflow.models.dagbag import DagBag
from airflow.models.dagrun import DagRun
from airflow.models.taskinstance import TaskInstance as TI
from airflow.utils.db import provide_session
from airflow.utils.state import State
from airflow_queue_stats.models import Queue, Worker
from sqlalchemy import and_, func, or_, tuple_


@provide_session
def get_backlog(session):
    backlog = dict(
        (
            session.query(TI.queue, func.count()).filter(
                or_(
                    # This case is unfinished, but not yet queued, tasks
                    # In some cases, the task state can be null,
                    # which we will choose to ignore
                    and_(
                        TI.queued_dttm.is_(None),
                        TI.state.isnot(None),
                        TI.state.notin_(State.finished()),
                    )
                ),
                TI.state.in_([State.QUEUED]),
            )
        )
        .group_by(TI.queue)
        .all()
    )

    queues = []
    for queue, count in backlog.items():
        q = Queue(name=queue, backlog=count)
        queues.append(q)

    return queues


def get_dags():
    dagbag = DagBag()
    return dagbag.dags


@provide_session
def get_unfinished_task_instances(session):
    task_instances = (
        session.query(TI).filter(
            or_(TI.queued_dttm.is_(None), TI.state.in_([State.QUEUED, State.RUNNING]))
        )
    ).all()
    return task_instances


@provide_session
def get_dag_runs(task_instances, session):

    dag_runs = (
        session.query(DagRun).filter(
            tuple_(DagRun.dag_id, DagRun.execution_date).in_(
                [
                    (task_instance.dag_id, task_instance.execution_date)
                    for task_instance in task_instances
                ]
            )
        )
    ).all()
    return dag_runs


def get_workers():
    workers_inspection = celery_app.control.inspect()

    raw_data = {}
    raw_data["stats"] = workers_inspection.stats()
    raw_data["active_queues"] = workers_inspection.active_queues()
    raw_data["active"] = workers_inspection.active()

    workers = {}

    if raw_data["stats"] is not None:
        for worker_name, data in raw_data["stats"].items():
            if worker_name not in workers:
                workers[worker_name] = Worker(name=worker_name, stats=data)
            else:
                workers[worker_name].stats = data

    if raw_data["active_queues"] is not None:
        for worker_name, data in raw_data["active_queues"].items():
            if worker_name not in workers:
                workers[worker_name] = Worker(name=worker_name, active_queues=data)
            else:
                workers[worker_name].active_queues = data

    if raw_data["active"] is not None:
        for worker_name, data in raw_data["active"].items():
            if worker_name not in workers:
                workers[worker_name] = Worker(name=worker_name, active=data)
            else:
                workers[worker_name].active = data

    return list(workers.values())
