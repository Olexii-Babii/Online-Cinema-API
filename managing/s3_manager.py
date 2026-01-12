from typing import Union

import aioboto3
from botocore.exceptions import HTTPClientError, NoCredentialsError, BotoCoreError

from config.settings import Settings


class S3Client():
    def __init__(self, settings: Settings):
        self.settings = settings
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.S3_STORAGE_SECRET_KEY,
        )

    async def upload_image(
            self,
            file_name: str,
            file_data: Union[bytes, bytearray]
    ):
        try:
            async with self.session.client(
                    "s3", endpoint_url=self.settings.S3_STORAGE_ENDPOINT
            ) as client:
                await client.put_object(
                    Bucket=self.settings.S3_STORAGE_BUCKET,
                    Key=file_name,
                    Body=file_data,
                    ContentType="image/jpeg",
                )
        except (ConnectionError, HTTPClientError, NoCredentialsError) as e:
            raise ConnectionError(f"Failed to connect to S3 storage: {str(e)}")
        except BotoCoreError as e:
            raise BotoCoreError(f"Failed to upload to S3 storage: {str(e)}")

    async def get_file_url(self, file_name: str) -> str:
        return f"{self.settings.S3_STORAGE_ENDPOINT}/{self.settings.S3_BUCKET_NAME}/{file_name}"
