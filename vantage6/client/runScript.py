import json
import requests
import time
import docker

# connect to service
headerData = {
    'Content-Type': "application/json"
}

# Init configuration file
configFile = open("config.json")
clientData = json.load(configFile)
configFile.close()

# Init docker
dockerClient = docker.from_env()

if "id" not in clientData:
    # execute HTTP POST to try and authenticate
    resp = requests.post("http://localhost:5000/client/add", data=json.dumps(clientData), headers=headerData)
    respObj = json.loads(resp.text)
    clientId = respObj.get('clientId', '')
    clientData["id"] = clientId
    configFile = open("config.json", "w")
    json.dump(clientData, configFile)
    configFile.close()

print("Starting with client ID " + str(clientData["id"]))

while True:
    taskList = list()

    # Connect to central host, if fails do nothing
    try:
        resp = requests.get("http://localhost:5000/client/" + str(clientData["id"]) + "/task")
        taskList = json.loads(resp.text)
    except:
        print("Could not retrieve result from master.")

    # If no task retrieved (or central host down) wait again
    if len(taskList) == 0:
        print("Waiting....")
        time.sleep(clientData["interval"])

    # If there are tasks retrieved, proces task list
    iTask = 0
    while iTask < len(taskList):
        myTask = taskList[iTask]
        taskId = myTask.get('id')
        image = myTask.get('image')
        inputArgs = myTask.get("input")
        imageResponse = ""

        logResult = dockerClient.containers.run(image)

        responseData = {
            'response': logResult
        }

        # execute HTTP POST to send back result (response)
        resp = requests.post(
            "http://localhost:5000/client/" + str(clientData["id"]) + "/task/" + str(taskId) + "/result/add",
            data=json.dumps(responseData), headers=headerData)
        respObjResult = json.loads(resp.text)
        print("resultId" + str(respObjResult["taskId"]))
        iTask += 1
