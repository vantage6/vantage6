from azure.storage.blob import BlobServiceClient
import config

connection_string = config.connection_string

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
container_name = config.container_name

container_client = blob_service_client.get_container_client(container_name)

container_client.delete_container()