from helper import web_server
from helper.scheduler import MyScheduler

scheduler = MyScheduler()
web_server.start(heating=scheduler)

try:
    scheduler.start()
except KeyboardInterrupt:
    pass
finally:
    scheduler.stop()
