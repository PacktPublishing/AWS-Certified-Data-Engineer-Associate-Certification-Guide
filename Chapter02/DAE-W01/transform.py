import io
import json
import uuid
import boto3
import numpy as np
import pandas as pd
import urllib.parse
import awswrangler as wr
from decimal import Decimal

s3 = boto3.client('s3')
ddb_resource = boto3.resource('dynamodb')
pd.set_option('future.no_silent_downcasting', True)

def lambda_handler(event, context):
    # print("Received event: " + json.dumps(event, indent=2))
    print("Object created: "+event['Records'][0]['s3']['object']['key'])
    
    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    
    # Construct the ARN
    s3_arn = f"arn:aws:s3:::{bucket}/{key}"
    
    try:
        
        print("Processing object: "+key)
        response = s3.get_object(Bucket=bucket, Key=key)
        
        print("Decoding CSV body")
        csv_content = response['Body'].read().decode('utf-8')
        
        print("Creating a pandas dataframe based on the contents")
        dataFrame = pd.read_csv(io.StringIO(csv_content))
        
        print("Dropping first 2 rows - [0, 1]")
        dataFrame = dataFrame.drop(index=[0, 1])
        
        print("Replace all empty records with 0 - fillna(0)")
        dataFrame = dataFrame.fillna(0)
        
        # Create a list of UUIDs, one for each row in the DataFrame
        uuids = [str(uuid.uuid4()) for _ in range(len(dataFrame))]
        
        # Insert the new 'uuid' column at the beginning of the DataFrame (position 0)
        dataFrame.insert(0, 'uuid', uuids)
        
        # Insert the new 'key' column at the beginning of the DataFrame (position 1)
        dataFrame.insert(1, 'object_key', s3_arn)
        
        # Define your DynamoDB table name
        table_name = '' # Your table name to be added here!

        print("Convert float values to Decimal for DynamoDB compatibility")
        # Convert float columns to Decimal
        for col in dataFrame.select_dtypes(include=['float']).columns:
            dataFrame[col] = dataFrame[col].apply(lambda x: Decimal(str(x)))
            
        print("Push DataFrame to DynamoDB")
        wr.dynamodb.put_df(df=dataFrame, table_name=table_name)
        
        print("File loaded into DynamoDB table successfully.")
        
    except Exception as e:
        print(e)
        print({
            "statusCode": 500,
            "body": {
                "exception": str(e),
                "message": "Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.".format(key, bucket)
                }
            })
