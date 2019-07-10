""" Create a docker image from this file called: `test-slave`.

Can't reach the outside world. Has access to the data-mount.

"""
import requests
import time
import logging 

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

log = logging.getLogger("main")
log.setLevel(logging.DEBUG)

log.info("slave - slave read mount...")
with open("/mnt/data/one.txt") as f:
    log.info(f"slave - {f.read()}")

log.info("slave - Start inf loop!")
while True:
    log.info("Woop loop!")
    should_fail = requests.get("https://nu.nl")
    log.info(should_fail.status_code)
    time.sleep(2)
