import json
import boto3

from aws_lambda_powertools.utilities.idempotency import (
    IdempotencyConfig,
    DynamoDBPersistenceLayer,
    idempotent,
)
from aws_lambda_powertools import Logger

logger = Logger()

# 1) Create a DynamoDB persistence layer for your table
persistence_layer = DynamoDBPersistenceLayer(table_name="cyber_restore_indempotency")

# 2) Define how to derive a unique ID from the event
#    We'll assume the S3 event is stored in event["Records"][0]["body"], 
#    and inside that JSON there's a "Records" array with s3 info. 
#    We'll pick the "sequencer" as the unique ID. 
config = IdempotencyConfig(
    event_key_jmespath="Records[0].s3.object.sequencer"
)

# 3) Decorate the core logic function
@idempotent(config=config, persistence_store=persistence_layer)
def process_s3_upload(event):
    """
    This function will run only once for each unique sequencer value.
    If the same event is delivered again, Powertools will skip re-running
    the logic and return the previously stored result.
    """

    # For SQS -> Lambda, the real S3 event is typically in "Records[].body"
    # So let's parse out the S3 event payload:
    s3_event_str = event["Records"][0]["body"]  # string
    s3_event = json.loads(s3_event_str)

    # Now let's get the bucket name and key from the real S3 event
    s3_record = s3_event["Records"][0]
    bucket = s3_record["s3"]["bucket"]["name"]
    key = s3_record["s3"]["object"]["key"]

    logger.info(f"Processing S3 upload from bucket={bucket}, key={key}")

    # 1. Download the file from S3
    s3_client = boto3.client("s3")
    response = s3_client.get_object(Bucket=bucket, Key=key)
    file_content = response["Body"].read().decode("utf-8")

    # 2. Parse the JSON to see which resources we need to restore
    #    e.g., { "resourceType": "dynamodb", "tableName": "...", etc. }
    restore_payload = json.loads(file_content)
    resource_type = restore_payload.get("resourceType")

    # 3. Start the relevant Step Functions workflow
    stepfunctions_client = boto3.client("stepfunctions")

    if resource_type == "dynamodb":
        logger.info("Launching DynamoDB restore state machine...")
        # Example: start a state machine
        stepfunctions_client.start_execution(
            stateMachineArn="arn:aws:states:us-east-1:123456789012:stateMachine:DynamoRestore",
            input=json.dumps(restore_payload),
        )
    elif resource_type == "rds":
        logger.info("Launching RDS restore state machine...")
        stepfunctions_client.start_execution(
            stateMachineArn="arn:aws:states:us-east-1:123456789012:stateMachine:RdsRestore",
            input=json.dumps(restore_payload),
        )
    else:
        logger.warning("Resource type unknown or not provided. Skipping.")

    # Return a result that Powertools will cache in DynamoDB
    return {"status": "processed", "resourceType": resource_type}


def lambda_handler(event, context):
    """
    Primary AWS Lambda handler.
    - 'event' includes SQS messages containing S3 event notifications.
    - We'll call our @idempotent function, which ensures each S3 event
      is processed once based on the 'sequencer' ID.
    """
    result = process_s3_upload(event)
    logger.info(f"Result: {result}")
    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }




#https://aws.amazon.com/blogs/compute/handling-lambda-functions-idempotency-with-aws-lambda-powertools/
#https://docs.powertools.aws.dev/lambda/python/latest/utilities/idempotency/

#By combining expires_after_seconds in your IdempotencyConfig and enabling DynamoDB TTL on the expiry attribute, 
#you ensure old event records eventually drop off.