from azure.storage.blob import BlobServiceClient
import config

connection_string = config.connection_string

blob_service_client = BlobServiceClient.from_connection_string(connection_string)

print("Containers:")
for container in blob_service_client.list_containers():
    print(f" - {container.name}")

container_client = blob_service_client.get_container_client(config.container_name)

print(f"\nBlobs in '{config.container_name}':")
for blob in container_client.list_blobs():
    blobdata = container_client.download_blob(blob.name).readall()
    print("name------------------------------------------------")
    print(f"{blob.name}")
    print("blobdata------------------------------------------------")
    print(f"{blobdata[:100]}")