from flask import Flask, Response, request, send_file, abort
import json
import sqlite3
import os
import uuid

app = Flask('FileService')

#create upload folder if not exists
storageDir = "storage"
if not os.path.exists(storageDir):
    os.mkdir(storageDir)

app = Flask('FileService')

@app.route('/')
def index():
    return "Hello, World"

@app.route('/addFile', methods=["POST"])
def postFile():
    #generate uuid for file
    uuidFile = str(uuid.uuid4())
    print("uuid: " + uuidFile)

    #store file in folder, using uuid
    fileObj = request.files.get("fileObj")
    fileObj.save(os.path.join(storageDir, uuidFile))

    #give response object
    data = {
        'status': "success",
        'uuid': uuidFile
    }
    return Response(json.dumps(data), mimetype="application/json")

@app.route('/file/<string:uuidFile>')
def getFile(uuidFile):
    if not (request.remote_addr == '127.0.0.1') or (request.remote_addr == '10.0.*.*'):
        abort(403)  # Forbidden

    filePath = os.path.join(storageDir, uuidFile)
    if os.path.exists(filePath):
        return send_file(filePath, attachment_filename=uuidFile)
    else:
        abort(404)

app.run(debug=True, host='0.0.0.0', port=5001)