# swagger template
swagger_template = {
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": " JWT"
            }
        },
        "schemas": {
            "Task": {
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Name of the algorithm's Docker image"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable task description"
                    },
                    "input": {
                        "type": "string",
                        "description": "Task input"
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable task name"
                    },
                    "collaboration_id": {
                        "type": "integer",
                        "description": "Collaboration id"
                    },
                    "organizations": {
                        "type": "array",
                        "items": {"type": "dictionary"},
                        "description": (
                            "List of organizations for who the task is "
                            "intended. For each organization, the 'id' and "
                            "'input' fields should be specified."
                        )
                    },
                    "databases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Databases to use for this task"
                    }
                },
                "example": {
                    "name": "human-readable-name",
                    "image": "hello-world",
                    "collaboration_id": 1,
                    "description": "human-readable-description",
                    "organizations": [{
                        "id": 1,
                        "input": "input-for-organization-1"
                    }],
                    "databases": ["database1", "database2"],
                },
                "required": ["image", "collaboration_id"]
            },
            "Organization": {
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name"
                    },
                    "address1": {
                        "type": "string",
                        "description": "Address line 1"
                    },
                    "address2": {
                        "type": "string",
                        "description": "Address line 2"
                    },
                    "zipcode": {
                        "type": "string",
                        "description": "Zip code"
                    },
                    "country": {
                        "type": "string",
                        "description": "Country"
                    },
                    "public_key": {
                        "type": "string",
                        "description":
                            "Public key. Note that this should be public key "
                            "*only*, i.e. without any metadata."
                    },
                    "domain": {
                        "type": "string",
                        "description": "Link to website of the organization."
                    }
                },
                "example": {
                    "name": "organization-name",
                    "address1": "Sunshine lane 1234",
                    "address2": "Miami, Florida",
                    "zipcode": "1234 LA",
                    "country": "USA",
                    "public_key": "a_public_key",
                    "domain": "organization.edu"
                },
            },
            "Collaboration": {
                "properties": {
                    "collaboration_id": {"type": "integer"}
                },
                "example": {
                    "collaboration_id": 1
                }
            },
            "Node": {
                "example": {
                    "api_key": "unique-uuid-string"
                },
                "properties": {
                    "api_key": {
                        "type": "string"
                    }
                }
            },
            "User": {
                "example": {
                    "password": "secret!",
                    "username": "yourname"
                },
                "properties": {
                    "password": {"type": "string"},
                    "username": {"type": "string"}
                }
            },
            "ContainerToken": {
                "properties": {
                    "task_id": {"type": "string"},
                    "image": {"type": "string"}
                },
                "example": {
                    "task_id": 1,
                    "image": "hello-world"
                }
            }
        }
    },
    "security": [
        {"bearerAuth": []}
    ]
}
