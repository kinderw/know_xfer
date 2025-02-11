import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from your_module import check_dynamodb_table_exists  # Replace 'your_module' with your file name

class TestDynamoDBTableCheck(unittest.TestCase):
    @patch('boto3.client')
    def test_table_exists(self, mock_boto_client):
        # Mock the describe_table to return a successful response
        mock_dynamodb = MagicMock()
        mock_dynamodb.describe_table.return_value = {'Table': {'TableName': 'TestTable'}}
        mock_boto_client.return_value = mock_dynamodb
        
        result = check_dynamodb_table_exists('TestTable')
        self.assertTrue(result)
    
    @patch('boto3.client')
    def test_table_not_found(self, mock_boto_client):
        # Mock the describe_table to raise ResourceNotFoundException
        mock_dynamodb = MagicMock()
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Requested resource not found'}}
        mock_dynamodb.describe_table.side_effect = ClientError(error_response, 'DescribeTable')
        mock_boto_client.return_value = mock_dynamodb
        
        result = check_dynamodb_table_exists('NonExistentTable')
        self.assertFalse(result)

    @patch('boto3.client')
    def test_unexpected_error(self, mock_boto_client):
        # Mock the describe_table to raise a different exception
        mock_dynamodb = MagicMock()
        error_response = {'Error': {'Code': 'InternalServerError', 'Message': 'Internal server error'}}
        mock_dynamodb.describe_table.side_effect = ClientError(error_response, 'DescribeTable')
        mock_boto_client.return_value = mock_dynamodb
        
        with self.assertRaises(ClientError):
            check_dynamodb_table_exists('AnyTable')

if __name__ == '__main__':
    unittest.main()
