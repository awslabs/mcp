# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the OpenAPI validator module."""

from awslabs.openapi_mcp_server.utils.openapi_validator import (
    extract_api_structure,
    find_pagination_endpoints,
    validate_openapi_spec,
)
from unittest.mock import MagicMock, patch


class TestOpenAPIValidator:
    """Test cases for OpenAPI validator functions."""

    def test_validate_openapi_spec_valid(self):
        """Test validation of a valid OpenAPI spec."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        assert validate_openapi_spec(spec) is True

    def test_validate_openapi_spec_missing_openapi(self):
        """Test validation with missing openapi field."""
        spec = {
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        assert validate_openapi_spec(spec) is False

    def test_validate_openapi_spec_missing_info(self):
        """Test validation with missing info field."""
        spec = {
            'openapi': '3.0.0',
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        assert validate_openapi_spec(spec) is False

    def test_validate_openapi_spec_missing_paths(self):
        """Test validation with missing paths field."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
        }
        assert validate_openapi_spec(spec) is False

    def test_validate_openapi_spec_unsupported_version(self):
        """Test validation with unsupported OpenAPI version."""
        spec = {
            'openapi': '2.0.0',  # Unsupported version
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }
        # Should still pass basic validation but log a warning
        assert validate_openapi_spec(spec) is True

    def test_validate_openapi_spec_with_openapi_core(self):
        """Test validation using openapi-core if available."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Mock the create_spec method
            mock_create_spec = MagicMock()
            mock_openapi_core.create_spec = mock_create_spec

            assert validate_openapi_spec(spec) is True
            mock_create_spec.assert_called_once_with(spec)

    def test_validate_openapi_spec_with_openapi_core_exception(self):
        """Test validation when openapi-core raises an exception."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Mock the create_spec method to raise an exception
            mock_create_spec = MagicMock(side_effect=Exception('Test exception'))
            mock_openapi_core.create_spec = mock_create_spec

            # Should still return True as we already passed basic validation
            assert validate_openapi_spec(spec) is True

    def test_validate_openapi_spec_with_openapi_spec_class(self):
        """Test validation using OpenAPISpec class if available."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Remove create_spec attribute
            if hasattr(mock_openapi_core, 'create_spec'):
                del mock_openapi_core.create_spec

            # Remove Spec attribute
            if hasattr(mock_openapi_core, 'Spec'):
                del mock_openapi_core.Spec

            # Mock the OpenAPISpec class with create method
            mock_openapi_spec_class = MagicMock()
            mock_create = MagicMock()
            mock_openapi_spec_class.create = mock_create
            mock_openapi_core.OpenAPISpec = mock_openapi_spec_class

            assert validate_openapi_spec(spec) is True

            # The validation function should have called OpenAPISpec.create
            mock_create.assert_called_once_with(spec)

    def test_validate_openapi_spec_with_spec_class(self):
        """Test validation using Spec class if available."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Remove create_spec attribute
            del mock_openapi_core.create_spec

            # Remove OpenAPISpec attribute
            if hasattr(mock_openapi_core, 'OpenAPISpec'):
                del mock_openapi_core.OpenAPISpec

            # Mock the Spec class
            mock_spec = MagicMock()
            mock_spec.create = MagicMock()
            mock_openapi_core.Spec = mock_spec

            assert validate_openapi_spec(spec) is True
            mock_spec.create.assert_called_once_with(spec)

    def test_validate_openapi_spec_with_unsupported_openapi_core(self):
        """Test validation with unsupported openapi-core version."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
        }

        # Mock both the availability and the module itself
        with (
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.OPENAPI_CORE_AVAILABLE', True
            ),
            patch('awslabs.openapi_mcp_server.utils.openapi_validator.USE_OPENAPI_CORE', True),
            patch(
                'awslabs.openapi_mcp_server.utils.openapi_validator.openapi_core'
            ) as mock_openapi_core,
        ):
            # Remove all supported attributes
            if hasattr(mock_openapi_core, 'create_spec'):
                del mock_openapi_core.create_spec
            if hasattr(mock_openapi_core, 'OpenAPISpec'):
                del mock_openapi_core.OpenAPISpec
            if hasattr(mock_openapi_core, 'Spec'):
                del mock_openapi_core.Spec

            # Should still pass validation
            assert validate_openapi_spec(spec) is True

    def test_extract_api_structure_basic(self):
        """Test extraction of API structure with basic spec."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0', 'description': 'A test API'},
            'paths': {
                '/test': {
                    'get': {
                        'operationId': 'getTest',
                        'summary': 'Get test',
                        'description': 'Get a test resource',
                        'responses': {'200': {'description': 'OK'}},
                    }
                }
            },
        }

        structure = extract_api_structure(spec)

        assert structure['info']['title'] == 'Test API'
        assert structure['info']['version'] == '1.0.0'
        assert structure['info']['description'] == 'A test API'
        assert '/test' in structure['paths']
        assert 'get' in structure['paths']['/test']['methods']
        assert structure['paths']['/test']['methods']['get']['operationId'] == 'getTest'
        assert len(structure['operations']) == 1
        assert structure['operations'][0]['operationId'] == 'getTest'
        assert structure['operations'][0]['method'] == 'GET'
        assert structure['operations'][0]['path'] == '/test'

    def test_extract_api_structure_with_parameters(self):
        """Test extraction of API structure with parameters."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/test/{id}': {
                    'get': {
                        'operationId': 'getTestById',
                        'parameters': [
                            {
                                'name': 'id',
                                'in': 'path',
                                'required': True,
                                'description': 'The test ID',
                            },
                            {
                                'name': 'filter',
                                'in': 'query',
                                'required': False,
                                'description': 'Filter results',
                            },
                        ],
                        'responses': {'200': {'description': 'OK'}},
                    }
                }
            },
        }

        structure = extract_api_structure(spec)

        assert '/test/{id}' in structure['paths']
        assert 'get' in structure['paths']['/test/{id}']['methods']
        parameters = structure['paths']['/test/{id}']['methods']['get']['parameters']
        assert len(parameters) == 2
        assert parameters[0]['name'] == 'id'
        assert parameters[0]['in'] == 'path'
        assert parameters[0]['required'] is True
        assert parameters[1]['name'] == 'filter'
        assert parameters[1]['in'] == 'query'
        assert parameters[1]['required'] is False

    def test_extract_api_structure_with_request_body(self):
        """Test extraction of API structure with request body."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/test': {
                    'post': {
                        'operationId': 'createTest',
                        'requestBody': {
                            'required': True,
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'type': 'object',
                                        'properties': {'name': {'type': 'string'}},
                                    }
                                }
                            },
                        },
                        'responses': {'201': {'description': 'Created'}},
                    }
                }
            },
        }

        structure = extract_api_structure(spec)

        assert '/test' in structure['paths']
        assert 'post' in structure['paths']['/test']['methods']
        request_body = structure['paths']['/test']['methods']['post']['requestBody']
        assert request_body['required'] is True
        assert 'application/json' in request_body['content_types']

    def test_extract_api_structure_with_responses(self):
        """Test extraction of API structure with responses."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/test': {
                    'get': {
                        'operationId': 'getTest',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {'application/json': {'schema': {'type': 'object'}}},
                            },
                            '404': {'description': 'Not Found'},
                        },
                    }
                }
            },
        }

        structure = extract_api_structure(spec)

        assert '/test' in structure['paths']
        assert 'get' in structure['paths']['/test']['methods']
        responses = structure['paths']['/test']['methods']['get']['responses']
        assert '200' in responses
        assert '404' in responses
        assert responses['200']['description'] == 'OK'
        assert 'application/json' in responses['200']['content_types']
        assert responses['404']['description'] == 'Not Found'
        assert responses['404']['content_types'] == []

    def test_extract_api_structure_with_schemas(self):
        """Test extraction of API structure with schemas."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'responses': {'200': {'description': 'OK'}}}}},
            'components': {
                'schemas': {
                    'Test': {
                        'type': 'object',
                        'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}},
                        'required': ['id'],
                    },
                    'Error': {
                        'type': 'object',
                        'properties': {'code': {'type': 'integer'}, 'message': {'type': 'string'}},
                    },
                }
            },
        }

        structure = extract_api_structure(spec)

        assert len(structure['schemas']) == 2
        test_schema = next((s for s in structure['schemas'] if s['name'] == 'Test'), None)
        assert test_schema is not None
        assert test_schema['type'] == 'object'
        assert test_schema['properties'] == 2
        assert 'id' in test_schema['required']

        error_schema = next((s for s in structure['schemas'] if s['name'] == 'Error'), None)
        assert error_schema is not None
        assert error_schema['type'] == 'object'
        assert error_schema['properties'] == 2
        assert error_schema['required'] == []

    def test_extract_api_structure_missing_fields(self):
        """Test extraction of API structure with missing fields."""
        spec = {
            'openapi': '3.0.0',
            # Missing info
            'paths': {
                '/test': {
                    # Missing method details
                }
            },
        }

        structure = extract_api_structure(spec)

        assert structure['info']['title'] == 'Unknown API'
        assert structure['info']['version'] == 'Unknown'
        assert structure['info']['description'] == ''
        assert '/test' in structure['paths']
        assert structure['paths']['/test']['methods'] == {}
        assert len(structure['operations']) == 0
        assert len(structure['schemas']) == 0

    def test_find_pagination_endpoints_with_pagination_params(self):
        """Test finding pagination endpoints with pagination parameters."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/tests': {
                    'get': {
                        'operationId': 'listTests',
                        'parameters': [
                            {
                                'name': 'page',
                                'in': 'query',
                                'required': False,
                                'description': 'Page number',
                            },
                            {
                                'name': 'limit',
                                'in': 'query',
                                'required': False,
                                'description': 'Items per page',
                            },
                        ],
                        'responses': {'200': {'description': 'OK'}},
                    }
                },
                '/items': {
                    'get': {
                        'operationId': 'listItems',
                        'parameters': [
                            {
                                'name': 'offset',
                                'in': 'query',
                                'required': False,
                                'description': 'Offset',
                            },
                            {
                                'name': 'size',
                                'in': 'query',
                                'required': False,
                                'description': 'Size',
                            },
                        ],
                        'responses': {'200': {'description': 'OK'}},
                    }
                },
                '/users': {
                    'get': {
                        'operationId': 'listUsers',
                        'parameters': [
                            {
                                'name': 'filter',
                                'in': 'query',
                                'required': False,
                                'description': 'Filter',
                            }
                        ],
                        'responses': {'200': {'description': 'OK'}},
                    }
                },
            },
        }

        pagination_endpoints = find_pagination_endpoints(spec)

        assert len(pagination_endpoints) == 2
        paths = [endpoint[0] for endpoint in pagination_endpoints]
        assert '/tests' in paths
        assert '/items' in paths
        assert '/users' not in paths

    def test_find_pagination_endpoints_with_array_response(self):
        """Test finding pagination endpoints with array responses."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/tests': {
                    'get': {
                        'operationId': 'listTests',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {
                                    'application/json': {
                                        'schema': {'type': 'array', 'items': {'type': 'object'}}
                                    }
                                },
                            }
                        },
                    }
                },
                '/items': {
                    'get': {
                        'operationId': 'listItems',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'items': {
                                                    'type': 'array',
                                                    'items': {'type': 'object'},
                                                },
                                                'total': {'type': 'integer'},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                '/users': {
                    'get': {
                        'operationId': 'listUsers',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {
                                                'data': {
                                                    'type': 'array',
                                                    'items': {'type': 'object'},
                                                },
                                                'pagination': {'type': 'object'},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
                '/products': {
                    'get': {
                        'operationId': 'listProducts',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {
                                    'application/json': {
                                        'schema': {
                                            'type': 'object',
                                            'properties': {'count': {'type': 'integer'}},
                                        }
                                    }
                                },
                            }
                        },
                    }
                },
            },
        }

        pagination_endpoints = find_pagination_endpoints(spec)

        assert len(pagination_endpoints) == 3
        paths = [endpoint[0] for endpoint in pagination_endpoints]
        assert '/tests' in paths
        assert '/items' in paths
        assert '/users' in paths
        assert '/products' not in paths

    def test_find_pagination_endpoints_non_get_methods(self):
        """Test finding pagination endpoints with non-GET methods."""
        spec = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API', 'version': '1.0.0'},
            'paths': {
                '/tests': {
                    'post': {
                        'operationId': 'createTest',
                        'parameters': [
                            {
                                'name': 'page',
                                'in': 'query',
                                'required': False,
                                'description': 'Page number',
                            }
                        ],
                        'responses': {'201': {'description': 'Created'}},
                    }
                },
                '/items': {
                    'put': {
                        'operationId': 'updateItem',
                        'responses': {
                            '200': {
                                'description': 'OK',
                                'content': {
                                    'application/json': {
                                        'schema': {'type': 'array', 'items': {'type': 'object'}}
                                    }
                                },
                            }
                        },
                    }
                },
            },
        }

        pagination_endpoints = find_pagination_endpoints(spec)

        # Should be empty as we only consider GET methods
        assert len(pagination_endpoints) == 0
