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
                    "session_id": {
                        "type": "integer",
                        "description": "Session id to which this task belongs",
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
                    "store_id": {
                        "type": "integer",
                        "description": "ID of the algorithm store from which the "
                        "algorithm is to be fetched",
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
                    "store_id": 1,
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
                        "description": "Domain name of the organization",
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
            "Session": {
                "properties": {
                    "name": {"type": "string"},
                    "collaboration_id": {"type": "integer"},
                    "study_id": {"type": "integer"},
                    "scope": {"type": "string"},
                },
                "example": {
                    "name": "unique-session-label",
                    "collaboration_id": 1,
                    "scope": "own",
                },
            },
            "DataFrame": {
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Label of the source database",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name of the DataFrame",
                    },
                    "task": {
                        "type": "object",
                        "description": "Data extraction task",
                    },
                },
                "example": {
                    "label": "database-label",
                    "name": "my-data-frame",
                    "task": {
                        "image": "hello-world",
                        "organizations": [
                            {
                                "id": 1,
                                "input": "encrypted-encoded-serialized-dict",
                            }
                        ],
                    },
                },
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
