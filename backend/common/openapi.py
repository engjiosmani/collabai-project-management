HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'head', 'options'}

STANDARD_ERROR_RESPONSES = {
    '400': {
        'description': 'Bad request. The submitted data is invalid or cannot be processed.',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                'examples': {
                    'validationError': {
                        'summary': 'Validation error',
                        'value': {'detail': 'Invalid request data.'},
                    }
                },
            }
        },
    },
    '401': {
        'description': 'Authentication credentials were not provided or are invalid.',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                'examples': {
                    'unauthorized': {
                        'summary': 'Unauthorized',
                        'value': {'detail': 'Authentication credentials were not provided.'},
                    }
                },
            }
        },
    },
    '403': {
        'description': 'The authenticated user does not have permission to perform this action.',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                'examples': {
                    'forbidden': {
                        'summary': 'Forbidden',
                        'value': {'detail': 'You do not have permission to perform this action.'},
                    }
                },
            }
        },
    },
    '404': {
        'description': 'The requested resource was not found.',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                'examples': {
                    'notFound': {
                        'summary': 'Not found',
                        'value': {'detail': 'Not found.'},
                    }
                },
            }
        },
    },
    '429': {
        'description': 'Too many requests. The API throttle limit has been exceeded.',
        'content': {
            'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorResponse'},
                'examples': {
                    'throttled': {
                        'summary': 'Rate limited',
                        'value': {'detail': 'Request was throttled.'},
                    }
                },
            }
        },
    },
}

TAG_DESCRIPTIONS = {
    'Auth': 'Registration, login, logout, token refresh, and password reset endpoints.',
    'Organizations': 'Organization, membership, and invitation management endpoints.',
    'Workspaces': 'Workspace, workspace member, and job role endpoints.',
    'Projects': 'Project and project membership endpoints.',
    'Tasks': 'Task, task metadata, labels, and attachment endpoints.',
    'Comments': 'Task comments and activity log endpoints.',
    'AI Assistant': 'AI assistant, semantic search, RAG, and team pulse endpoints.',
    'Notifications': 'Notification listing and read-state endpoints.',
    'Audit': 'Audit, operational metrics, health, dashboard, and schema endpoints.',
    'Profile': 'User profile, current user, password, and membership endpoints.',
}

TAG_BY_PREFIX = (
    ('/api/v1/auth/', 'Auth'),
    ('/api/v1/ai/', 'AI Assistant'),
    ('/api/v1/notifications/', 'Notifications'),
    ('/api/v1/audit/', 'Audit'),
    ('/api/v1/activity-logs/', 'Comments'),
    ('/api/v1/comments/', 'Comments'),
    ('/api/v1/projects/', 'Projects'),
    ('/api/v1/tasks/', 'Tasks'),
    ('/api/v1/task-statuses/', 'Tasks'),
    ('/api/v1/task-priorities/', 'Tasks'),
    ('/api/v1/job-roles/', 'Workspaces'),
    ('/api/v1/profile/', 'Profile'),
    ('/api/v1/users/', 'Profile'),
    ('/api/v1/invites/', 'Organizations'),
    ('/api/v1/organizations/', 'Organizations'),
    ('/api/v1/dashboard/', 'Audit'),
    ('/api/v1/health/', 'Audit'),
    ('/api/v1/metrics/', 'Audit'),
    ('/api/schema/', 'Audit'),
)

ACTION_BY_METHOD = {
    'get': 'Retrieve',
    'post': 'Create',
    'put': 'Replace',
    'patch': 'Update',
    'delete': 'Delete',
}


def _tag_for_path(path):
    if '/workspaces/' in path:
        return 'Workspaces'
    for prefix, tag in TAG_BY_PREFIX:
        if path.startswith(prefix):
            return tag
    return 'Audit'


def _resource_name(path):
    cleaned = path.strip('/').replace('{', '').replace('}', '')
    parts = [part for part in cleaned.split('/') if part and part not in {'api', 'v1'}]
    names = [part for part in parts if not part.endswith('_id') and part not in {'id', 'pk', 'token'}]
    if not names:
        return 'API schema'
    last = names[-1].replace('-', ' ').replace('_', ' ')
    return last.title()


def _summary_for(method, path):
    if path == '/api/schema/':
        return 'Retrieve OpenAPI schema'
    resource = _resource_name(path)
    action = ACTION_BY_METHOD.get(method, method.upper())
    if method == 'get' and '{' not in path:
        action = 'List'
    return f'{action} {resource}'


def _description_for(method, path, tag):
    summary = _summary_for(method, path).lower()
    return (
        f'{summary.capitalize()} for the {tag} API area. '
        'Successful responses and standard error responses are documented for Swagger UI testing.'
    )


def _ensure_components(result):
    components = result.setdefault('components', {})
    schemas = components.setdefault('schemas', {})
    schemas.setdefault(
        'ErrorResponse',
        {
            'type': 'object',
            'description': 'Standard API error response.',
            'properties': {
                'detail': {
                    'type': 'string',
                    'description': 'Human-readable error message.',
                }
            },
            'additionalProperties': True,
        },
    )
    security_schemes = components.setdefault('securitySchemes', {})
    bearer_scheme = {
        'type': 'http',
        'scheme': 'bearer',
        'bearerFormat': 'JWT',
    }
    security_schemes.setdefault('bearerAuth', bearer_scheme)
    security_schemes.setdefault('jwtAuth', bearer_scheme)


def complete_openapi_schema(result, generator, request, public):
    _ensure_components(result)
    result['tags'] = [
        {'name': name, 'description': description}
        for name, description in TAG_DESCRIPTIONS.items()
    ]
    result['security'] = [{'bearerAuth': []}]

    for path, path_item in result.get('paths', {}).items():
        tag = _tag_for_path(path)
        for method, operation in path_item.items():
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            operation['tags'] = [tag]
            operation.setdefault('summary', _summary_for(method, path))
            operation.setdefault('description', _description_for(method, path, tag))
            operation.setdefault('security', [{'bearerAuth': []}])

            responses = operation.setdefault('responses', {})
            for status_code, response in STANDARD_ERROR_RESPONSES.items():
                responses.setdefault(status_code, response)

    return result
