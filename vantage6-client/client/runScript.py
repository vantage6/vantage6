import json, requests

#connect to service
headerData = {
    'Content-Type': "application/json"
}

clientData = {
    'name': "Johan van Soest",
    'email': "johan.vansoest@maastro.nl",
    'institute': 'MAASTRO Clinic',
    'country': 'Netherlands'
}
# execute HTTP POST to try and authenticate
resp = requests.post("http://localhost:5000/client/add", data=json.dumps(clientData), headers=headerData)
respObj = json.loads(resp.text)
clientId = respObj.get('clientId', '')

while True:
    resp = requests.get("http://localhost:5000/client/"+str(clientId)+"/task")
    respObjTask = json.loads(resp.text)

    if len(respObjTask) == 0:
        print("nothing to do....")
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
            resp = requests.post("http://localhost:5000/client/" + str(clientId) + "/task/" + str(taskId) + "/add", data=json.dumps(clientData), headers=headerData)
            respObjResult = json.loads(resp.text)
            resultId = respObjResult.get('resultId', '')
            print("resultId" + str(resultId))
