from helper import web_server
from helper.scheduler import MyScheduler

scheduler = MyScheduler()
web_server.start()

try:
    scheduler.start()
except KeyboardInterrupt:
    pass
finally:
    scheduler.stop()
