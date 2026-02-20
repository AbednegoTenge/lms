import boto3
from django.conf import settings

def generate_presigned_url(key, expiration=3600):
    """
    Generate a presigned URL for an S3 object.
    
    :param file_key: The key of the S3 object (e.g., 'assignments/course_code/assignment_id/filename')
    :param expiration: Time in seconds for the presigned URL to remain valid (default is 1 hour)
    :return: A presigned URL as a string
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )
    presigned_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": key
        },
        ExpiresIn=expiration
    )
    return presigned_url