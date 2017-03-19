from flask import Flask, Response, request
import json
from DbDao import DbDao

app = Flask('TaskMaster')
dbDao = DbDao()

@app.route('/')
def index():
    return "Hello, World"

@app.route('/client')
def clientList():
    clientList = dbDao.getClients()
    return Response(json.dumps(clientList), mimetype='application/json')

@app.route('/client/add', methods=["POST"])
def addClient():
    data = request.get_json()
    clientId = dbDao.addClient(data["name"], data["email"], data["institute"], data["country"], request.remote_addr)
    data = {
        'success': True,
        'clientId': clientId
    }
    return Response(json.dumps(data), mimetype="application/json")

@app.route('/client/<int:clientId>/task')
def getClientTasks(clientId):
    openTasks = dbDao.getClientOpenTasks(clientId)
    return Response(json.dumps(openTasks), mimetype='application/json')

@app.route('/client/<int:clientId>/task/add', methods=["POST"])
def addClientTask(clientId):
    data = request.get_json()
    taskId = dbDao.addTask(clientId, data["image"], data["inputString"])
    data = {
        'success': True,
        'taskId': taskId
    }
    return Response(json.dumps(data), mimetype="application/json")

@app.route('/client/<int:clientId>/task/<int:taskId>/result')
def getTaskResult(clientId, taskId):
    taskResult = dbDao.getTaskResult(taskId)
    return Response(json.dumps(taskResult), mimetype='application/json')

@app.route('/client/<int:clientId>/task/<int:taskId>/result/add', methods=["POST"])
def addTaskResult(clientId, taskId):
    data = request.get_json()
    resultId = dbDao.addTaskResult(taskId, data["response"])
    data = {
        'success': True,
        'taskId': resultId
    }
    return Response(json.dumps(data), mimetype="application/json")

app.run(debug=True, host='0.0.0.0', port=5000)