import os
from django import setup
from apscheduler.schedulers.blocking import BlockingScheduler

sched = BlockingScheduler()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "napoleon.settings.local")
setup()


@sched.scheduled_job('cron', hour=0)
def scheduled_finish_room():
    print('finish room every day')
    from napoleon.room.management.commands.finish_room import Command    
    cmd = Command()
    cmd.handle(**{"days": 1})


sched.start()
