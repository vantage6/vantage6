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
                    "image": {"type": "string"},
                    "description": {"type": "string"},
                    "input": {"type": "string"},
                    "name": {"type": "string"},
                    "collaboration_id": {"type": "integer"},
                    "organization_ids": {
                        "type": "array",
                        "items": {"type": "integer"}
                    }
                },
                "example": {
                    "name": "human-readable-name",
                    "image": "hello-world",
                    "collaboration_id": 1
                },
                "required": ["image", "collaboration_id"]
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
                    "api_key": "unique-string"
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
