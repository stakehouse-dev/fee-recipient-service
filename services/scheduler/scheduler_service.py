import services
from multiprocessing import Process
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import threading
import time
import atexit
from api import app
from apiconfig import APIConfig

config = APIConfig()
Scheduler_Object = BackgroundScheduler()
Scheduler_Object.add_jobstore(
    SQLAlchemyJobStore(
        url="mysql+pymysql://" + config.db("connection_string")
        ),
    "default",
)


class Scheduler(object):
    def __init__(self):
        pass

    def running(self):
        """Get true whether the scheduler is running."""
        return Scheduler_Object.running

    @property
    def state(self):
        """Get the state of the scheduler."""
        return Scheduler_Object.state

    @property
    def scheduler(self):
        """Get the base scheduler."""
        return Scheduler_Object

    def start(self, paused=False):
        Scheduler_Object.start(paused=paused)

    def shutdown(self, wait=True):
        if self.state == 1:
            print("Scheduler called to shutdown")
            Scheduler_Object.shutdown(wait)
            print("Scheduler shutdown")
        else:
            print("Scheduler was not running on shutdown call")

    def pause(self):
        Scheduler_Object.pause()

    def resume(self):
        Scheduler_Object.resume()

    def add_job(self, **kwargs):
        return Scheduler_Object.add_job(**kwargs)

    def delete_job(self, id, jobstore=None):
        Scheduler_Object.remove_job(id, jobstore)

    def remove_job(self, id, jobstore=None):
        Scheduler_Object.remove_job(id, jobstore)

    def remove_all_jobs(self, jobstore=None):
        Scheduler_Object.remove_all_jobs(jobstore)

    def get_job(self, id, jobstore=None):
        return Scheduler_Object.get_job(id, jobstore)

    def get_jobs(self, jobstore=None):
        return Scheduler_Object.get_jobs(jobstore)

    def modify_job(self, id, jobstore=None, **changes):
        return Scheduler_Object.modify_job(id, jobstore, **changes)

    def pause_job(self, id, jobstore=None):
        Scheduler_Object.pause_job(id, jobstore)

    def resume_job(self, id, jobstore=None):
        Scheduler_Object.resume_job(id, jobstore)


@app.on_event("startup")
async def initialize_Scheduler():
    print("Server: Starting up Scheduler")
    if Scheduler_Object.state == 0:
        Scheduler_Object.start()

    atexit.register(lambda: Scheduler().shutdown())

    print(
        "Scheduler status: ", ("Alive" if Scheduler_Object.state == 1 else "Not alive")
    )

    return Scheduler_Object
