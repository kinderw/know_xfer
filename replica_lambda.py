import boto3
import json

def lambda_handler(event, context):
    response = {}

    if 'replicaCheck' in event:
        config_string = event['replicaCheck']
        response['replicas_exist'] = check_replicas(config_string)

    return response

def check_replicas(config_string):
    try:
        config = json.loads(config_string)
    except json.JSONDecodeError as e:
        return False  # If the config can't be parsed, assume no replicas

    replicas = config.get('Replicas', [])

    if not replicas:
        return False  # No replicas in the configuration

    for replica in replicas:
        region = replica.get('RegionName')
        table_name = replica.get('TableName')

        if not region or not table_name:
            continue  # Skip incomplete replica information

        try:
            dynamodb_client = boto3.client('dynamodb', region_name=region)
            dynamodb_client.describe_table(TableName=table_name)
            return True  # Replica exists
        except dynamodb_client.exceptions.ResourceNotFoundException:
            continue  # Replica doesn't exist in this region
        except Exception as e:
            print(f"Error checking replica in {region}: {str(e)}")
            continue

    return False  # No replicas found after checking all regions
