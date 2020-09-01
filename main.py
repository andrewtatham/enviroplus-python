from helper.scheduler import MyScheduler

scheduler = MyScheduler()

try:
    scheduler.start()
except KeyboardInterrupt:
    pass
finally:
    scheduler.stop()
