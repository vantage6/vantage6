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
    respObjTask = json.loads(resp.text)

    if len(respObjTask) == 0:
        print("nothing to do....")
        time.sleep(clientData["interval"])
    else :
        
        taskId = respObjTask.get('id')
        image = respObjTask.get('image')
        inputArgs = respObjTask.get("input")

        if image is "hello-world":
            print("found hello-world!")
            clientData = {
                'response': "Hello, world!"
            }
            # execute HTTP POST to try and authenticate
            resp = requests.post("http://localhost:5000/client/" + str(clientData["id"]) + "/task/" + str(taskId) + "/add", data=json.dumps(clientData), headers=headerData)
            respObjResult = json.loads(resp.text)
            resultId = respObjResult.get('resultId', '')
            print("resultId" + str(resultId))
