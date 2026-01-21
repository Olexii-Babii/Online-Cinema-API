from typing import Dict, Union


class FakeS3Client():
    def __init__(self):
        self.storage: Dict[str, bytes] = {}

    async def upload_file(self, file_name: str, file_data: Union[bytes, bytearray]) -> None:
        self.storage[file_name] = file_data

    async def get_file_url(self, file_name: str) -> str:
        return f"http://fake-s3.local/{file_name}"