class BaseModel:
    pass


class Worker(BaseModel):
    def __init__(self, name, stats=None, active_queues=None, active=None):
        self.name = name
        self._stats = stats
        self._active_queues = active_queues if active_queues is not None else []
        self._active = active if active is not None else []

    @property
    def active(self):
        return self._active

    @active.setter
    def active(self, value):
        self._active = value

    @property
    def active_count(self):
        return len(self.active)

    @property
    def active_queues(self):
        return self._active_queues

    @active_queues.setter
    def active_queues(self, value):
        self._active_queues = value

    @property
    def queue_names(self):
        return [queue["name"] for queue in self.active_queues]

    @property
    def stats(self):
        return self._stats

    @stats.setter
    def stats(self, value):
        self._stats = value

    def queues(self):
        pass

    @property
    def capacity(self):
        return self.max_capacity - len(self._active)

    @property
    def max_capacity(self):
        return min(
            self._stats["pool"]["max-concurrency"],
            len(self._stats["pool"]["processes"]),
        )


class Queue(BaseModel):
    def __init__(self, name, workers=None, backlog=0, active=None, desired_usage=0):
        self.name = name
        self.backlog = backlog
        self.desired_usage = desired_usage

        self.workers = workers[:] if workers is not None else []
        self.active = active[:] if active is not None else []

    @property
    def active_count(self):
        return len(self.active)

    @property
    def capacity(self):
        return max(self.max_capacity - self.active_count, 0)

    @property
    def max_capacity(self):
        return sum([worker.max_capacity for worker in self.workers])
