import collections

from airflow.utils.state import State
from airflow_queue_stats.models import Queue


def get_desired_usage(task_instances, dags, dag_runs):
    from airflow import configuration

    parallelism = configuration.conf.getint("core", "PARALLELISM")
    max_running_by_dag = collections.defaultdict(int)
    max_running_by_queue = collections.defaultdict(int)

    task_instances_by_dag_run = collections.defaultdict(list)
    task_instances_by_dag_run_queue = collections.defaultdict(
        lambda: collections.defaultdict(list)
    )
    for task_instance in task_instances:
        task_instances_by_dag_run[
            (task_instance.dag_id, task_instance.execution_date)
        ].append(task_instance)

        task_instances_by_dag_run_queue[
            (task_instance.dag_id, task_instance.execution_date)
        ][task_instance.queue].append(task_instance)

    dag_runs_by_dag = collections.defaultdict(list)
    dag_runs_by_queue = collections.defaultdict(list)
    for dag_run in dag_runs:
        dag_runs_by_dag[dag_run.dag_id].append(dag_run)
        dag_run_queue_instances = task_instances_by_dag_run_queue[
            (dag_run.dag_id, dag_run.execution_date)
        ].items()

        for queue, unfinished_task_instances in dag_run_queue_instances:
            dag_runs_by_queue[queue].append(dag_run)

    for dag_id, dag_dag_runs in dag_runs_by_dag.items():
        dag = dags[dag_id]
        max_active_runs = dag.max_active_runs
        concurrency = dag.concurrency

        # These dag runs have the most unfinished tasks
        worst_case_dag_runs = sorted(
            dag_dag_runs,
            key=lambda x: len(
                task_instances_by_dag_run[(dag_run.dag_id, dag_run.execution_date)]
            ),
            reverse=True,
        )[:max_active_runs]

        # Max theoretical is active runs * concurrency
        max_theoretical_running_tasks = max_active_runs * concurrency

        max_dag_run_tasks = sum(
            [
                min(
                    len(
                        task_instances_by_dag_run[
                            (dag_run.dag_id, dag_run.execution_date)
                        ]
                    ),
                    concurrency,
                )
                for dag_run in worst_case_dag_runs
            ]
        )

        max_running_by_dag[dag_id] = min(
            max_theoretical_running_tasks, max_dag_run_tasks
        )

    for queue, queue_dag_runs in dag_runs_by_queue.items():
        queue_task_instances_by_dag_runs = collections.defaultdict(dict)
        for dag_run in queue_dag_runs:
            queue_task_instances_by_dag_runs[dag_run.dag_id][
                dag_run.execution_date
            ] = task_instances_by_dag_run[(dag_run.dag_id, dag_run.execution_date)]

        for dag_id, executions in queue_task_instances_by_dag_runs.items():
            dag = dags[dag_id]
            max_active_runs = dag.max_active_runs
            concurrency = dag.concurrency
            worst_case_dag_run_task_instances = sorted(
                executions.values(), key=lambda x: len(x), reverse=True
            )[:max_active_runs]
            max_dag_run_tasks = sum(
                [
                    min(len(dag_run_task_instances), concurrency)
                    for dag_run_task_instances in worst_case_dag_run_task_instances
                ]
            )

            max_theoretical_running_tasks = max_active_runs * concurrency
            max_running_by_queue[queue] += min(
                max_dag_run_tasks, max_theoretical_running_tasks
            )

    total_max_running = min(parallelism, sum(max_running_by_dag.values()))

    if sum(max_running_by_queue.values()) > parallelism:
        # Pro Rate each queue value by the proportion
        total_wanted_to_run = sum(max_running_by_queue.values())
        for queue in max_running_by_queue.keys():
            # TODO: Account for priority
            max_running_by_queue[queue] = int(
                max_running_by_queue[queue] * parallelism / total_wanted_to_run
            )

    if sum(max_running_by_dag.values()) > parallelism:
        total_wanted_to_run = sum(max_running_by_dag.values())
        for dag_id in max_running_by_dag.keys():
            # TODO: Account for priority
            max_running_by_dag[dag_id] = int(
                max_running_by_dag[dag_id] * parallelism / total_wanted_to_run
            )

    return {
        "total": total_max_running,
        "by_dag": max_running_by_dag,
        "by_queue": max_running_by_queue,
    }


def consolidate_queues(task_instances, workers, backlogged_queues, desired_usage):
    queue_worker_lookup = collections.defaultdict(list)
    queue_info_lookup = collections.defaultdict(list)
    queue_backlog_lookup = {}
    queue_desired_usage_lookup = desired_usage["by_queue"]

    known_queues = set(desired_usage["by_queue"].keys())

    queues = []

    for worker in workers:
        for queue_info in worker.active_queues:
            queue_name = queue_info["name"]
            queue_worker_lookup[queue_name].append(worker)
            queue_info_lookup[queue_name] = queue_info
            known_queues.add(queue_name)

    for queue in backlogged_queues:
        queue_backlog_lookup[queue.name] = queue.backlog
        known_queues.add(queue.name)

    for queue_name in known_queues:
        active = [
            task_instance
            for task_instance in task_instances
            if task_instance.state == State.RUNNING
            and task_instance.queue == queue_name
        ]

        workers = queue_worker_lookup.get(queue_name, [])
        backlog = queue_backlog_lookup.get(queue_name, 0)
        desired_usage = queue_desired_usage_lookup.get(queue_name, 0)

        queues.append(
            Queue(
                name=queue_name,
                active=active,
                workers=workers,
                backlog=backlog,
                desired_usage=desired_usage,
            )
        )

    return queues
