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
                        "items": {"type": "integer"},
                        "description": (
                            "Organization ids in collaboration to create task "
                            "for"
                        )
                    },
                    "database": {
                        "type": "string",
                        "description": "Database to use for this task"
                    },
                    "master": {
                        "type": "boolean",
                        "description": (
                            "Whether or not this is a master task. Default "
                            "value is False"
                        )
                    }
                },
                "example": {
                    "name": "human-readable-name",
                    "image": "hello-world",
                    "collaboration_id": 1
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
