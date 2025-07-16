import pytest
from awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler import CrawlerHandler
from botocore.exceptions import ClientError
from unittest.mock import Mock, patch


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server instance for testing."""
    mcp = Mock()
    mcp.tool = Mock(return_value=lambda x: x)
    return mcp


@pytest.fixture
def mock_context():
    """Create a mock context for testing."""
    context = Mock()
    context.request_id = 'test-request-id'
    return context


@pytest.fixture
def handler(mock_mcp):
    """Create a CrawlerHandler instance with write access for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = CrawlerHandler(mock_mcp, allow_write=True)
        return handler


@pytest.fixture
def no_write_handler(mock_mcp):
    """Create a CrawlerHandler instance without write access for testing."""
    with patch(
        'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
    ) as mock_aws_helper:
        mock_aws_helper.create_boto3_client.return_value = Mock()
        handler = CrawlerHandler(mock_mcp, allow_write=False)
        return handler


class TestCrawlerHandler:
    """Test class for CrawlerHandler functionality."""

    @pytest.mark.asyncio
    async def test_init(self, mock_mcp):
        """Test initialization of CrawlerHandler."""
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.create_boto3_client.return_value = Mock()

            handler = CrawlerHandler(mock_mcp, allow_write=True, allow_sensitive_data_access=True)

            assert handler.mcp == mock_mcp
            assert handler.allow_write is True
            assert handler.allow_sensitive_data_access is True
            mock_aws_helper.create_boto3_client.assert_called_once_with('glue')

            assert mock_mcp.tool.call_count == 3

            call_args_list = mock_mcp.tool.call_args_list

            tool_names = [call_args[1]['name'] for call_args in call_args_list]

            assert 'manage_aws_glue_crawlers' in tool_names
            assert 'manage_aws_glue_classifiers' in tool_names
            assert 'manage_aws_glue_crawler_management' in tool_names

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_create_success(self, handler, mock_context):
        """Test successful creation of a Glue crawler."""
        # Setup
        handler.glue_client.create_crawler.return_value = {}

        # Mock AwsHelper methods
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.prepare_resource_tags.return_value = {
                'ManagedBy': 'DataprocessingMcpServer'
            }

            # Test
            result = await handler.manage_aws_glue_crawlers(
                mock_context,
                operation='create-crawler',
                crawler_name='test-crawler',
                crawler_definition={
                    'Role': 'test-role',
                    'Targets': {'S3Targets': [{'Path': 's3://test-bucket/'}]},
                    'DatabaseName': 'test-db',
                    'Description': 'Test crawler',
                    'Schedule': 'cron(0 0 * * ? *)',
                    'TablePrefix': 'test_',
                    'Tags': {'custom': 'tag'},
                },
            )

            # Assertions
            assert result.isError is False
            assert result.crawler_name == 'test-crawler'
            assert result.operation == 'create-crawler'
            handler.glue_client.create_crawler.assert_called_once()
            mock_aws_helper.prepare_resource_tags.assert_called_once_with('GlueCrawler')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_create_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that creating a crawler fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawlers(
            mock_context,
            operation='create-crawler',
            crawler_name='test-crawler',
            crawler_definition={
                'Role': 'test-role',
                'Targets': {'S3Targets': [{'Path': 's3://test-bucket/'}]},
            },
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.create_crawler.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_create_missing_role(self, handler, mock_context):
        """Test that creating a crawler without a role raises ValueError."""
        with pytest.raises(ValueError, match='Role is required'):
            await handler.manage_aws_glue_crawlers(
                mock_context,
                operation='create-crawler',
                crawler_name='test-crawler',
                crawler_definition={'Targets': {'S3Targets': [{'Path': 's3://test-bucket/'}]}},
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_create_missing_targets(self, handler, mock_context):
        """Test that creating a crawler without targets raises ValueError."""
        with pytest.raises(ValueError, match='Targets is required'):
            await handler.manage_aws_glue_crawlers(
                mock_context,
                operation='create-crawler',
                crawler_name='test-crawler',
                crawler_definition={'Role': 'test-role'},
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_delete_success(self, handler, mock_context):
        """Test successful deletion of a Glue crawler."""
        # Setup
        handler.glue_client.get_crawler.return_value = {'Crawler': {'Parameters': {}}}
        handler.glue_client.delete_crawler.return_value = {}

        # Mock AwsHelper methods
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            # Test
            result = await handler.manage_aws_glue_crawlers(
                mock_context, operation='delete-crawler', crawler_name='test-crawler'
            )

            # Assertions
            assert result.isError is False
            assert result.crawler_name == 'test-crawler'
            assert result.operation == 'delete-crawler'
            handler.glue_client.delete_crawler.assert_called_once_with(Name='test-crawler')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_delete_not_mcp_managed(self, handler, mock_context):
        """Test deletion of a crawler not managed by MCP."""
        # Setup
        handler.glue_client.get_crawler.return_value = {'Crawler': {'Parameters': {}}}

        # Mock AwsHelper methods
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = False

            # Test
            result = await handler.manage_aws_glue_crawlers(
                mock_context, operation='delete-crawler', crawler_name='test-crawler'
            )

            # Assertions
            assert result.isError is True
            assert 'not managed by the MCP server' in result.content[0].text
            handler.glue_client.delete_crawler.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_delete_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that deleting a crawler fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawlers(
            mock_context, operation='delete-crawler', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.delete_crawler.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_get_crawler_success(self, handler, mock_context):
        """Test successful retrieval of a Glue crawler."""
        # Setup
        crawler_details = {
            'Name': 'test-crawler',
            'Role': 'test-role',
            'Targets': {'S3Targets': [{'Path': 's3://test-bucket/'}]},
            'DatabaseName': 'test-db',
            'State': 'READY',
        }
        handler.glue_client.get_crawler.return_value = {'Crawler': crawler_details}

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='get-crawler', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.crawler_details == crawler_details
        assert result.operation == 'get-crawler'
        handler.glue_client.get_crawler.assert_called_once_with(Name='test-crawler')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_get_crawler_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that getting a crawler works without write access."""
        # Setup
        crawler_details = {
            'Name': 'test-crawler',
            'Role': 'test-role',
            'Targets': {'S3Targets': [{'Path': 's3://test-bucket/'}]},
            'DatabaseName': 'test-db',
            'State': 'READY',
        }
        no_write_handler.glue_client.get_crawler.return_value = {'Crawler': crawler_details}

        # Test
        result = await no_write_handler.manage_aws_glue_crawlers(
            mock_context, operation='get-crawler', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.crawler_details == crawler_details
        assert result.operation == 'get-crawler'

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_get_crawlers_success(self, handler, mock_context):
        """Test successful retrieval of all Glue crawlers."""
        # Setup
        crawlers = [
            {'Name': 'test-crawler-1', 'Role': 'test-role', 'State': 'READY'},
            {'Name': 'test-crawler-2', 'Role': 'test-role', 'State': 'RUNNING'},
        ]
        handler.glue_client.get_crawlers.return_value = {
            'Crawlers': crawlers,
            'NextToken': 'next-token',
        }

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='get-crawlers', max_results=10, next_token='token'
        )

        # Assertions
        assert result.isError is False
        assert result.crawlers == crawlers
        assert result.count == 2
        assert result.next_token == 'next-token'
        assert result.operation == 'get-crawlers'
        handler.glue_client.get_crawlers.assert_called_once_with(MaxResults=10, NextToken='token')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_start_crawler_success(self, handler, mock_context):
        """Test successful start of a Glue crawler."""
        # Setup
        handler.glue_client.start_crawler.return_value = {}

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='start-crawler', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.operation == 'start-crawler'
        handler.glue_client.start_crawler.assert_called_once_with(Name='test-crawler')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_start_crawler_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that starting a crawler fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawlers(
            mock_context, operation='start-crawler', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.start_crawler.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_stop_crawler_success(self, handler, mock_context):
        """Test successful stop of a Glue crawler."""
        # Setup
        handler.glue_client.stop_crawler.return_value = {}

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='stop-crawler', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.operation == 'stop-crawler'
        handler.glue_client.stop_crawler.assert_called_once_with(Name='test-crawler')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_stop_crawler_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that stopping a crawler fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawlers(
            mock_context, operation='stop-crawler', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.stop_crawler.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_batch_get_crawlers_success(
        self, handler, mock_context
    ):
        """Test successful batch retrieval of Glue crawlers."""
        # Setup
        crawlers = [
            {'Name': 'test-crawler-1', 'Role': 'test-role', 'State': 'READY'},
            {'Name': 'test-crawler-2', 'Role': 'test-role', 'State': 'RUNNING'},
        ]
        handler.glue_client.batch_get_crawlers.return_value = {
            'Crawlers': crawlers,
            'CrawlersNotFound': ['test-crawler-3'],
        }

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context,
            operation='batch-get-crawlers',
            crawler_names=['test-crawler-1', 'test-crawler-2', 'test-crawler-3'],
        )

        # Assertions
        assert result.isError is False
        assert result.crawlers == crawlers
        assert result.crawlers_not_found == ['test-crawler-3']
        assert result.operation == 'batch-get-crawlers'
        handler.glue_client.batch_get_crawlers.assert_called_once_with(
            CrawlerNames=['test-crawler-1', 'test-crawler-2', 'test-crawler-3']
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_list_crawlers_success(self, handler, mock_context):
        """Test successful listing of Glue crawlers."""
        # Setup
        handler.glue_client.list_crawlers.return_value = {
            'CrawlerNames': ['test-crawler-1', 'test-crawler-2'],
            'NextToken': 'next-token',
        }

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context,
            operation='list-crawlers',
            max_results=10,
            next_token='token',
            tags={'tag1': 'value1'},
        )

        # Assertions
        assert result.isError is False
        assert result.crawlers == ['test-crawler-1', 'test-crawler-2']
        assert result.count == 2
        assert result.next_token == 'next-token'
        assert result.operation == 'list-crawlers'
        handler.glue_client.list_crawlers.assert_called_once_with(
            MaxResults=10, NextToken='token', Tags={'tag1': 'value1'}
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_update_crawler_success(self, handler, mock_context):
        """Test successful update of a Glue crawler."""
        # Setup
        handler.glue_client.update_crawler.return_value = {}

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context,
            operation='update-crawler',
            crawler_name='test-crawler',
            crawler_definition={
                'Role': 'updated-role',
                'Targets': {'S3Targets': [{'Path': 's3://updated-bucket/'}]},
                'DatabaseName': 'updated-db',
                'Description': 'Updated crawler',
                'Schedule': 'cron(0 12 * * ? *)',
                'TablePrefix': 'updated_',
            },
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.operation == 'update-crawler'
        handler.glue_client.update_crawler.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_update_crawler_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that updating a crawler fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawlers(
            mock_context,
            operation='update-crawler',
            crawler_name='test-crawler',
            crawler_definition={
                'Role': 'updated-role',
                'Targets': {'S3Targets': [{'Path': 's3://updated-bucket/'}]},
            },
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.update_crawler.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_invalid_operation(self, handler, mock_context):
        """Test handling of invalid operation."""
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='invalid-operation', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_missing_crawler_name(self, handler, mock_context):
        """Test that operations requiring crawler_name raise ValueError when it's missing."""
        operations = ['get-crawler', 'start-crawler', 'stop-crawler', 'delete-crawler']

        for operation in operations:
            with pytest.raises(
                ValueError, match=f'crawler_name is required for {operation} operation'
            ):
                await handler.manage_aws_glue_crawlers(
                    mock_context, operation=operation, crawler_name=None
                )

        operations = ['create-crawler', 'update-crawler']

        for operation in operations:
            with pytest.raises(
                ValueError,
                match=f'crawler_name and crawler_definition are required for {operation} operation',
            ):
                await handler.manage_aws_glue_crawlers(
                    mock_context, operation=operation, crawler_name=None
                )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_missing_crawler_definition(
        self, handler, mock_context
    ):
        """Test that operations requiring crawler_definition raise ValueError when it's missing."""
        operations = ['create-crawler', 'update-crawler']

        for operation in operations:
            with pytest.raises(
                ValueError,
                match=f'crawler_name and crawler_definition are required for {operation} operation',
            ):
                await handler.manage_aws_glue_crawlers(
                    mock_context,
                    operation=operation,
                    crawler_name='test-crawler',
                    crawler_definition=None,
                )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_missing_crawler_names(self, handler, mock_context):
        """Test that batch-get-crawlers raises ValueError when crawler_names is missing."""
        with pytest.raises(
            ValueError, match='crawler_names is required for batch-get-crawlers operation'
        ):
            await handler.manage_aws_glue_crawlers(
                mock_context, operation='batch-get-crawlers', crawler_names=None
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_error_handling(self, handler, mock_context):
        """Test error handling when Glue API calls raise exceptions."""
        # Setup
        handler.glue_client.get_crawler.side_effect = Exception('Test error')

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='get-crawler', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_client_error(self, handler, mock_context):
        """Test handling of ClientError."""
        # Setup
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        handler.glue_client.get_crawler.side_effect = ClientError(error_response, 'GetCrawler')

        # Test
        result = await handler.manage_aws_glue_crawlers(
            mock_context, operation='get-crawler', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is True
        assert 'Error in manage_aws_glue_crawlers' in result.content[0].text
        assert 'Invalid input' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_delete_client_error(self, handler, mock_context):
        """Test handling of ClientError during crawler deletion."""
        # Setup
        error_response = {
            'Error': {'Code': 'EntityNotFoundException', 'Message': 'Crawler not found'}
        }
        handler.glue_client.get_crawler.side_effect = ClientError(error_response, 'GetCrawler')

        # Mock AwsHelper methods
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'

            # Test
            result = await handler.manage_aws_glue_crawlers(
                mock_context, operation='get-crawler', crawler_name='test-crawler'
            )

            # Assertions
            assert result.isError is True
            assert 'Error in manage_aws_glue_crawlers' in result.content[0].text
            assert 'Crawler not found' in result.content[0].text

    # Tests for manage_aws_glue_classifiers method
    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_success(self, handler, mock_context):
        """Test successful creation of a Glue classifier."""
        # Setup
        handler.glue_client.create_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='create-classifier',
            classifier_definition={
                'CsvClassifier': {
                    'Name': 'test-csv-classifier',
                    'Delimiter': ',',
                    'QuoteSymbol': '"',
                    'ContainsHeader': 'PRESENT',
                    'Header': ['id', 'name', 'date', 'value'],
                }
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-csv-classifier'
        assert result.operation == 'create-classifier'
        handler.glue_client.create_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that creating a classifier fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_classifiers(
            mock_context,
            operation='create-classifier',
            classifier_definition={
                'CsvClassifier': {'Name': 'test-csv-classifier', 'Delimiter': ','}
            },
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.create_classifier.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_missing_definition(
        self, handler, mock_context
    ):
        """Test that creating a classifier without definition raises ValueError."""
        with pytest.raises(ValueError, match='classifier_definition is required'):
            await handler.manage_aws_glue_classifiers(
                mock_context, operation='create-classifier', classifier_definition=None
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_invalid_definition(
        self, handler, mock_context
    ):
        """Test that creating a classifier with invalid definition raises ValueError."""
        with pytest.raises(ValueError, match='classifier_definition must include one of'):
            await handler.manage_aws_glue_classifiers(
                mock_context,
                operation='create-classifier',
                classifier_definition={'InvalidType': {}},
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_delete_success(self, handler, mock_context):
        """Test successful deletion of a Glue classifier."""
        # Setup
        handler.glue_client.delete_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context, operation='delete-classifier', classifier_name='test-classifier'
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-classifier'
        assert result.operation == 'delete-classifier'
        handler.glue_client.delete_classifier.assert_called_once_with(Name='test-classifier')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_delete_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that deleting a classifier fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_classifiers(
            mock_context, operation='delete-classifier', classifier_name='test-classifier'
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.delete_classifier.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_get_classifier_success(self, handler, mock_context):
        """Test successful retrieval of a Glue classifier."""
        # Setup
        classifier_details = {
            'CsvClassifier': {'Name': 'test-classifier', 'Delimiter': ',', 'QuoteSymbol': '"'}
        }
        handler.glue_client.get_classifier.return_value = {'Classifier': classifier_details}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context, operation='get-classifier', classifier_name='test-classifier'
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-classifier'
        assert result.classifier_details == classifier_details
        assert result.operation == 'get-classifier'
        handler.glue_client.get_classifier.assert_called_once_with(Name='test-classifier')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_get_classifiers_success(
        self, handler, mock_context
    ):
        """Test successful retrieval of all Glue classifiers."""
        # Setup
        classifiers = [
            {'CsvClassifier': {'Name': 'test-classifier-1', 'Delimiter': ','}},
            {'JsonClassifier': {'Name': 'test-classifier-2'}},
        ]
        handler.glue_client.get_classifiers.return_value = {
            'Classifiers': classifiers,
            'NextToken': 'next-token',
        }

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context, operation='get-classifiers', max_results=10, next_token='token'
        )

        # Assertions
        assert result.isError is False
        assert result.classifiers == classifiers
        assert result.count == 2
        assert result.next_token == 'next-token'
        assert result.operation == 'get-classifiers'
        handler.glue_client.get_classifiers.assert_called_once_with(
            MaxResults=10, NextToken='token'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_update_success(self, handler, mock_context):
        """Test successful update of a Glue classifier."""
        # Setup
        handler.glue_client.update_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='update-classifier',
            classifier_definition={
                'CsvClassifier': {
                    'Name': 'test-csv-classifier',
                    'Delimiter': '|',
                    'QuoteSymbol': '"',
                }
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-csv-classifier'
        assert result.operation == 'update-classifier'
        handler.glue_client.update_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_update_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that updating a classifier fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_classifiers(
            mock_context,
            operation='update-classifier',
            classifier_definition={
                'CsvClassifier': {'Name': 'test-csv-classifier', 'Delimiter': '|'}
            },
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.update_classifier.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_invalid_operation(self, handler, mock_context):
        """Test handling of invalid operation."""
        result = await handler.manage_aws_glue_classifiers(
            mock_context, operation='invalid-operation', classifier_name='test-classifier'
        )

        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_missing_classifier_name(
        self, handler, mock_context
    ):
        """Test that operations requiring classifier_name raise ValueError when it's missing."""
        operations = ['delete-classifier', 'get-classifier']

        for operation in operations:
            with pytest.raises(
                ValueError, match=f'classifier_name is required for {operation} operation'
            ):
                await handler.manage_aws_glue_classifiers(
                    mock_context, operation=operation, classifier_name=None
                )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_error_handling(self, handler, mock_context):
        """Test error handling when Glue API calls raise exceptions."""
        # Setup
        handler.glue_client.get_classifier.side_effect = Exception('Test error')

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context, operation='get-classifier', classifier_name='test-classifier'
        )

        # Assertions
        assert result.isError is True
        assert 'Test error' in result.content[0].text

    # Tests for manage_aws_glue_crawler_management method
    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_get_metrics_success(
        self, handler, mock_context
    ):
        """Test successful retrieval of crawler metrics."""
        # Setup
        metrics = [
            {
                'CrawlerName': 'test-crawler-1',
                'TimeLeftSeconds': 100,
                'StillEstimating': False,
                'LastRuntimeSeconds': 200,
            },
            {
                'CrawlerName': 'test-crawler-2',
                'TimeLeftSeconds': 0,
                'StillEstimating': False,
                'LastRuntimeSeconds': 150,
            },
        ]
        handler.glue_client.get_crawler_metrics.return_value = {
            'CrawlerMetricsList': metrics,
            'NextToken': 'next-token',
        }

        # Test
        result = await handler.manage_aws_glue_crawler_management(
            mock_context,
            operation='get-crawler-metrics',
            crawler_name_list=['test-crawler-1', 'test-crawler-2'],
            max_results=10,
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_metrics == metrics
        assert result.count == 2
        assert result.next_token == 'next-token'
        assert result.operation == 'get-crawler-metrics'
        handler.glue_client.get_crawler_metrics.assert_called_once_with(
            CrawlerNameList=['test-crawler-1', 'test-crawler-2'], MaxResults=10
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_start_schedule_success(
        self, handler, mock_context
    ):
        """Test successful start of a crawler schedule."""
        # Setup
        handler.glue_client.start_crawler_schedule.return_value = {}

        # Test
        result = await handler.manage_aws_glue_crawler_management(
            mock_context, operation='start-crawler-schedule', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.operation == 'start-crawler-schedule'
        handler.glue_client.start_crawler_schedule.assert_called_once_with(
            CrawlerName='test-crawler'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_start_schedule_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that starting a crawler schedule fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawler_management(
            mock_context, operation='start-crawler-schedule', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.start_crawler_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_stop_schedule_success(
        self, handler, mock_context
    ):
        """Test successful stop of a crawler schedule."""
        # Setup
        handler.glue_client.stop_crawler_schedule.return_value = {}

        # Test
        result = await handler.manage_aws_glue_crawler_management(
            mock_context, operation='stop-crawler-schedule', crawler_name='test-crawler'
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.operation == 'stop-crawler-schedule'
        handler.glue_client.stop_crawler_schedule.assert_called_once_with(
            CrawlerName='test-crawler'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_stop_schedule_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that stopping a crawler schedule fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawler_management(
            mock_context, operation='stop-crawler-schedule', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.stop_crawler_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_update_schedule_success(
        self, handler, mock_context
    ):
        """Test successful update of a crawler schedule."""
        # Setup
        handler.glue_client.update_crawler_schedule.return_value = {}

        # Test
        result = await handler.manage_aws_glue_crawler_management(
            mock_context,
            operation='update-crawler-schedule',
            crawler_name='test-crawler',
            schedule='cron(0 12 * * ? *)',
        )

        # Assertions
        assert result.isError is False
        assert result.crawler_name == 'test-crawler'
        assert result.operation == 'update-crawler-schedule'
        handler.glue_client.update_crawler_schedule.assert_called_once_with(
            CrawlerName='test-crawler', Schedule='cron(0 12 * * ? *)'
        )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_update_schedule_missing_schedule(
        self, handler, mock_context
    ):
        """Test that updating a crawler schedule without schedule raises ValueError."""
        with pytest.raises(ValueError, match='crawler_name and schedule are required'):
            await handler.manage_aws_glue_crawler_management(
                mock_context,
                operation='update-crawler-schedule',
                crawler_name='test-crawler',
                schedule=None,
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_invalid_operation(
        self, handler, mock_context
    ):
        """Test handling of invalid operation."""
        result = await handler.manage_aws_glue_crawler_management(
            mock_context, operation='invalid-operation', crawler_name='test-crawler'
        )

        assert result.isError is True
        assert 'Invalid operation' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_missing_crawler_name(
        self, handler, mock_context
    ):
        """Test that operations requiring crawler_name raise ValueError when it's missing."""
        operations = ['start-crawler-schedule', 'stop-crawler-schedule']

        for operation in operations:
            with pytest.raises(
                ValueError, match=f'crawler_name is required for {operation} operation'
            ):
                await handler.manage_aws_glue_crawler_management(
                    mock_context, operation=operation, crawler_name=None
                )

        operation = 'update-crawler-schedule'
        with pytest.raises(
            ValueError, match=f'crawler_name and schedule are required for {operation} operation'
        ):
            await handler.manage_aws_glue_crawler_management(
                mock_context, operation=operation, crawler_name=None
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_error_handling(self, handler, mock_context):
        """Test error handling when Glue API calls raise exceptions."""
        # Setup
        handler.glue_client.get_crawler_metrics.side_effect = Exception('Test error')

        # Test
        result = await handler.manage_aws_glue_crawler_management(
            mock_context, operation='get-crawler-metrics'
        )

        # Assertions
        assert result.isError is True
        assert 'Test error' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_update_crawler_schedule_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that updating a crawler schedule fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawler_management(
            mock_context,
            operation='update-crawler-schedule',
            crawler_name='test-crawler',
            schedule='cron(0 12 * * ? *)',
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.update_crawler_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_delete_with_parameters(self, handler, mock_context):
        """Test deletion of a crawler with parameters."""
        # Setup
        handler.glue_client.get_crawler.return_value = {
            'Crawler': {'Parameters': {'key': 'value'}}
        }
        handler.glue_client.delete_crawler.return_value = {}

        # Mock AwsHelper methods
        with patch(
            'awslabs.aws_dataprocessing_mcp_server.handlers.glue.crawler_handler.AwsHelper'
        ) as mock_aws_helper:
            mock_aws_helper.get_aws_region.return_value = 'us-east-1'
            mock_aws_helper.get_aws_account_id.return_value = '123456789012'
            mock_aws_helper.is_resource_mcp_managed.return_value = True

            # Test
            result = await handler.manage_aws_glue_crawlers(
                mock_context, operation='delete-crawler', crawler_name='test-crawler'
            )

            # Assertions
            assert result.isError is False
            assert result.crawler_name == 'test-crawler'
            assert result.operation == 'delete-crawler'
            handler.glue_client.delete_crawler.assert_called_once_with(Name='test-crawler')

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawlers_get_crawler_error(self, handler, mock_context):
        """Test error handling for get-crawler operation."""
        # Setup
        handler.glue_client.get_crawler.side_effect = ValueError('Test error')

        # Test
        with pytest.raises(ValueError, match='Test error'):
            await handler.manage_aws_glue_crawlers(
                mock_context, operation='get-crawler', crawler_name='test-crawler'
            )

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_grok_classifier(self, handler, mock_context):
        """Test successful creation of a Grok classifier."""
        # Setup
        handler.glue_client.create_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='create-classifier',
            classifier_definition={
                'GrokClassifier': {
                    'Name': 'test-grok-classifier',
                    'Classification': 'apache-log',
                    'GrokPattern': '%{COMMONAPACHELOG}',
                }
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-grok-classifier'
        assert result.operation == 'create-classifier'
        handler.glue_client.create_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_xml_classifier(self, handler, mock_context):
        """Test successful creation of an XML classifier."""
        # Setup
        handler.glue_client.create_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='create-classifier',
            classifier_definition={
                'XMLClassifier': {
                    'Name': 'test-xml-classifier',
                    'Classification': 'xml',
                    'RowTag': 'item',
                }
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-xml-classifier'
        assert result.operation == 'create-classifier'
        handler.glue_client.create_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_create_json_classifier(self, handler, mock_context):
        """Test successful creation of a JSON classifier."""
        # Setup
        handler.glue_client.create_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='create-classifier',
            classifier_definition={
                'JsonClassifier': {'Name': 'test-json-classifier', 'JsonPath': '$.records[*]'}
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-json-classifier'
        assert result.operation == 'create-classifier'
        handler.glue_client.create_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_update_grok_classifier(self, handler, mock_context):
        """Test successful update of a Grok classifier."""
        # Setup
        handler.glue_client.update_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='update-classifier',
            classifier_definition={
                'GrokClassifier': {
                    'Name': 'test-grok-classifier',
                    'Classification': 'apache-log',
                    'GrokPattern': '%{COMBINEDAPACHELOG}',
                }
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-grok-classifier'
        assert result.operation == 'update-classifier'
        handler.glue_client.update_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_update_xml_classifier(self, handler, mock_context):
        """Test successful update of an XML classifier."""
        # Setup
        handler.glue_client.update_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='update-classifier',
            classifier_definition={
                'XMLClassifier': {
                    'Name': 'test-xml-classifier',
                    'Classification': 'xml',
                    'RowTag': 'record',
                }
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-xml-classifier'
        assert result.operation == 'update-classifier'
        handler.glue_client.update_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_update_json_classifier(self, handler, mock_context):
        """Test successful update of a JSON classifier."""
        # Setup
        handler.glue_client.update_classifier.return_value = {}

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context,
            operation='update-classifier',
            classifier_definition={
                'JsonClassifier': {'Name': 'test-json-classifier', 'JsonPath': '$.items[*]'}
            },
        )

        # Assertions
        assert result.isError is False
        assert result.classifier_name == 'test-json-classifier'
        assert result.operation == 'update-classifier'
        handler.glue_client.update_classifier.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_classifiers_client_error(self, handler, mock_context):
        """Test handling of ClientError in classifiers."""
        # Setup
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        handler.glue_client.get_classifier.side_effect = ClientError(
            error_response, 'GetClassifier'
        )

        # Test
        result = await handler.manage_aws_glue_classifiers(
            mock_context, operation='get-classifier', classifier_name='test-classifier'
        )

        # Assertions
        assert result.isError is True
        assert 'Error in manage_aws_glue_classifiers' in result.content[0].text
        assert 'Invalid input' in result.content[0].text

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_update_schedule_no_write_access(
        self, no_write_handler, mock_context
    ):
        """Test that updating a crawler schedule fails when write access is disabled."""
        result = await no_write_handler.manage_aws_glue_crawler_management(
            mock_context,
            operation='update-crawler-schedule',
            crawler_name='test-crawler',
            schedule='cron(0 12 * * ? *)',
        )

        assert result.isError is True
        assert 'not allowed without write access' in result.content[0].text
        no_write_handler.glue_client.update_crawler_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_manage_aws_glue_crawler_management_client_error(self, handler, mock_context):
        """Test handling of ClientError in crawler management."""
        # Setup
        error_response = {'Error': {'Code': 'ValidationException', 'Message': 'Invalid input'}}
        handler.glue_client.get_crawler_metrics.side_effect = ClientError(
            error_response, 'GetCrawlerMetrics'
        )

        # Test
        result = await handler.manage_aws_glue_crawler_management(
            mock_context, operation='get-crawler-metrics'
        )

        # Assertions
        assert result.isError is True
        assert 'Error in manage_aws_glue_crawler_management' in result.content[0].text
        assert 'Invalid input' in result.content[0].text
