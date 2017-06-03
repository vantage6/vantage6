import json, requests, time

#connect to service
headerData = {
    'Content-Type': "application/json"
}

configFile = open("config.json")
clientData = json.load(configFile)
configFile.close()

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
    resp = requests.get("http://localhost:5000/client/"+str(clientData["id"])+"/task")
    taskList = json.loads(resp.text)

    if len(taskList) == 0:
        print("nothing to do....")
        time.sleep(clientData["interval"])

    iTask = 0
    while iTask < len(taskList):
        myTask = taskList[iTask]
        taskId = myTask.get('id')
        image = myTask.get('image')
        inputArgs = myTask.get("input")
        imageResponse = ""

        if image == "hello-world":
            print("found hello-world!")
            imageResponse = "Hello, world!"

        responseData = {
            'response': imageResponse
        }
        # execute HTTP POST to send back result (response)
        resp = requests.post("http://localhost:5000/client/" + str(clientData["id"]) + "/task/" + str(taskId) + "/result/add", data=json.dumps(responseData), headers=headerData)
        respObjResult = json.loads(resp.text)
        print("resultId" + str(respObjResult["taskId"]))
        iTask += 1
