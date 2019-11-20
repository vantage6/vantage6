import sys
import os
import signal
import logging
import subprocess

# from threading import Thread, Event
# from multiprocessing import Process

# from watchdog.observers import Observer
# from watchdog.events import LoggingEventHandler, FileSystemEventHandler

from vantage import util, node, constants


# class ReloadEventHandler(FileSystemEventHandler):
#     """Logs all the events captured."""

#     process = None
#     name = None
#     environment = None
    
#     def on_any_event(self, event):        
#         super().on_any_event(event)

#         print(event)

#         print(f"proc {self.process}")
#         if ReloadEventHandler.process:
#             print("attemt to close process")
#             # os.kill(self.process.pid, signal.SIGINT)
#             self.process.terminate()
#             self.process.join(5)

#             if self.process.exitcode is None:
#                 print("FORCE to close process")                
#                 # os.kill(self.process.pid, signal.SIGKILL)
#                 self.process.join(1)

#             print("start application")
            
#             process = Process(target=method, args=(name, environment))
#             process.start()

#             ReloadEventHandler.process = process
#         else:
#             print("process not started yet (?!)")


            #   
def start(name, environment):
    """Start the node instance.
    
    If no name or config is specified the default.yaml configuation is used. 
    In case the configuration file not exists, a questionaire is
    invoked to create one. Note that in this case it is not possible to
    specify specific environments for the configuration (e.g. test, 
    prod, acc). 

    """
    
    # create context
    ctx = util.DockerNodeContext(name, environment)

    # run the node application
    node.run(ctx)

def start_development(name, environment):
    ctx = util.NodeContext(name, environment)
    node.run(ctx)

if __name__ == "__main__":

    # configuration name
    name = sys.argv[1]
    
    # environment in the config file (dev, test, acc, prod, application)
    environment = sys.argv[2]

    # run_process restarts the app when the source changes. The dev-local
    # is or a non dockerized version of the node, while the dev-docker is
    # specifically for the dockerized version
    
    if len(sys.argv) > 3:
        
        if sys.argv[3] == "dev-local":
            method = start_development
        elif sys.argv[3] == "dev-docker":
            method = start
        else:
            print(f"Option not recognised: {sys.argv[3]}")
        
        # event_handler = ReloadEventHandler()
        # observer = Observer()
        # observer.schedule(event_handler, 
        #     str(constants.PACAKAGE_FOLDER), recursive=True)
        # observer.start()
        # print(f"reload folder={constants.PACAKAGE_FOLDER}")

        method(name,environment)
        # print("starting multiprocess")
        # process = Process(target=method, args=(name, environment))
        # process.start()

        # ReloadEventHandler.process = process
        # ReloadEventHandler.name = name
        # ReloadEventHandler.environment = environment
        # ReloadEventHandler.observer = observer


        # try:
        #     import time
        #     while True:
        #         time.sleep(1)
        # except KeyboardInterrupt:
        #     observer.stop()
        # observer.join()
    else:
        # run script to start
        start(name, environment)