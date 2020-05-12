import os

import boto3 as boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


class S3:
    def __init__(self):
        """
            Constructor for S3 class, initializing and defining variables.
        """
        self.bucket_name = os.getenv("BUCKET_NAME")
        self.aws_access_key_id = os.getenv("AWS_BUCKET_ID")
        self.aws_secret_access_key = os.getenv("AWS_BUCKET_ACCESS_ID")
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
        )

    def upload_file(self, file_path, file_name):
        """
            Upload file to s3 Bucket
        
        Arguments:
            file_path (String): Path of file 
            file_name (String): Name of file 
        """
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, file_name)
        except ClientError as client_error:
            print(client_error)

    def download_json_date(self, json_file_name, json_file_path):
        """
            download last back up date file from s3 bucket.
        
        Arguments:
            json_file_name (String): Name of json file 
            json_file_path (String): Name of json file 
        """
        try:
            self.s3_client.download_file(
                self.bucket_name, json_file_name, json_file_path
            )
        except ClientError as client_error:
            print(client_error)
