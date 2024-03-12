# swagger template
swagger_template = {
    "components": {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": " JWT"}
        },
        "schemas": {
            "Task": {
                "properties": {
                    "image": {
                        "type": "string",
                        "description": "Name of the algorithm's Docker image",
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable task description",
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable task name",
                    },
                    "collaboration_id": {
                        "type": "integer",
                        "description": (
                            "Collaboration id. You do not need to provide this if you "
                            "provide a study id (but you can if you want to)."
                        ),
                    },
                    "study_id": {
                        "type": "integer",
                        "description": (
                            "Study id. You should only provide this if you want to "
                            "create a task for a specific study. Otherwise, you should "
                            "provide just a collaboration id."
                        ),
                    },
                    "organizations": {
                        "type": "dict",
                        "description": (
                            "List of organizations that should run the task. "
                            "The key 'id' should give the organization id, and"
                            " the key 'input' should give the input for that "
                            "organization. Each input should be a encrypted "
                            "and/or serialized dictionary that may contain the"
                            " keys 'method', kwargs', 'args'."
                        ),
                    },
                    "databases": {
                        "type": "array",
                        "items": {"type": "dict"},
                        "description": "Databases to use for this task",
                    },
                },
                "example": {
                    "name": "human-readable-name",
                    "image": "hello-world",
                    "collaboration_id": 1,
                    "description": "human-readable-description",
                    "organizations": [
                        {
                            "id": 1,
                            "input": {
                                "method": "method-name",
                                "kwargs": {"key": "value"},
                                "args": ["arg1", "arg2"],
                            },
                        }
                    ],
                    "databases": [
                        {
                            "label": "database-label",
                            "query": "SELECT * FROM table",
                            "preprocessing": [
                                {
                                    "type": "filter_range",
                                    "parameters": {
                                        "column": "column-name",
                                        "min": 0,
                                        "max": 10,
                                    },
                                }
                            ],
                        }
                    ],
                },
                "required": ["image", "collaboration_id"],
            },
            "Organization": {
                "properties": {
                    "name": {"type": "string", "description": "Name"},
                    "address1": {"type": "string", "description": "Address line 1"},
                    "address2": {"type": "string", "description": "Address line 2"},
                    "zipcode": {"type": "string", "description": "Zip code"},
                    "country": {"type": "string", "description": "Country"},
                    "public_key": {
                        "type": "string",
                        "description": "Public key. Note that this should be public key "
                        "*only*, i.e. without any metadata.",
                    },
                    "domain": {
                        "type": "string",
                        "description": "Link to website of the organization.",
                    },
                },
                "example": {
                    "name": "organization-name",
                    "address1": "Sunshine lane 1234",
                    "address2": "Miami, Florida",
                    "zipcode": "1234 LA",
                    "country": "USA",
                    "public_key": "a_public_key",
                    "domain": "organization.edu",
                },
            },
            "Collaboration": {
                "properties": {"collaboration_id": {"type": "integer"}},
                "example": {"collaboration_id": 1},
            },
            "Node": {
                "example": {"api_key": "unique-uuid-string"},
                "properties": {"api_key": {"type": "string"}},
            },
            "User": {
                "example": {"password": "secret!", "username": "yourname"},
                "properties": {
                    "password": {"type": "string"},
                    "username": {"type": "string"},
                },
            },
            "ContainerToken": {
                "properties": {
                    "task_id": {"type": "string"},
                    "image": {"type": "string"},
                },
                "example": {"task_id": 1, "image": "hello-world"},
            },
        },
    },
    "security": [{"bearerAuth": []}],
}
