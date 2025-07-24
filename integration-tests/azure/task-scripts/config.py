# config.py

server_url = "http://localhost"
server_port = 7601
server_api = "/api"

username = "alpha-user"
password = "alpha-password"

organization_key = "./privkey_alpha.pem"

connection_string = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;" \
                    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;" \
                    "BlobEndpoint=http://localhost:10000/devstoreaccount1;QueueEndpoint=http://localhost:10001/devstoreaccount1;"
container_name = "test-container"