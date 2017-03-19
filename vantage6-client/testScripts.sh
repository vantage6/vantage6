#add client
curl -H "Content-Type: application/json" -X POST -d '{"name": "johan", "email": "johan.vansoest@maastro.nl", "institute": "MAASTRO Clinic", "country": "Netherlands"}' http://localhost:5000/client/add

# http://localhost:5000/client

#add task to client
curl -H "Content-Type: application/json" -X POST -d '{"image": "hello-world", "inputString": ""}' http://localhost:5000/client/1/task/add

# http://localhost:5000/client/1/task

#add result to task
curl -H "Content-Type: application/json" -X POST -d '{"response": "Hello, world!"}' http://localhost:5000/client/1/task/1/result/add

# http://localhost:5000/client/1/task/1/result