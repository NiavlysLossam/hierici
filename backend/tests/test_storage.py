import pytest
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.services.storage.local import LocalStorageDriver
from app.services.storage.s3 import S3StorageDriver
from app.services.storage import get_storage_driver


@pytest.fixture
def temp_storage():
    temp_dir = tempfile.mkdtemp()
    driver = LocalStorageDriver(base_dir=temp_dir)
    yield driver, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_local_storage_lifecycle(temp_storage):
    driver, temp_dir = temp_storage
    test_content = b"Contenu de test pour HierIci"
    test_path = "photos/1912/test_image.webp"

    # 1. Sauvegarde
    url = await driver.save(test_content, test_path, content_type="image/webp")
    assert url == "/uploads/photos/1912/test_image.webp"

    # 2. Vérification existence
    exists = await driver.exists(test_path)
    assert exists is True

    # 3. Lecture
    content = await driver.read(test_path)
    assert content == test_content

    # 4. Suppression
    deleted = await driver.delete(test_path)
    assert deleted is True

    # 5. Vérification post-suppression
    exists_after = await driver.exists(test_path)
    assert exists_after is False

    with pytest.raises(FileNotFoundError):
        await driver.read(test_path)


@pytest.mark.asyncio
async def test_local_storage_path_traversal_prevention(temp_storage):
    driver, temp_dir = temp_storage
    with pytest.raises(ValueError):
        await driver.save(b"bad", "../../etc/passwd")
    with pytest.raises(ValueError):
        await driver.save(b"bad", "../" + Path(temp_dir).name + "_sibling/hack.txt")


@pytest.mark.asyncio
async def test_s3_storage_driver_mocked():
    from botocore.exceptions import ClientError

    with patch("boto3.client") as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        s3_driver = S3StorageDriver(
            bucket_name="test-bucket",
            endpoint_url="https://s3.fr-par.scw.cloud",
            access_key_id="dummy_key",
            secret_access_key="dummy_secret",
            region="fr-par",
        )

        test_data = b"image_data_s3"
        dest_path = "photos/2026/vue.webp"

        # Test Save
        url = await s3_driver.save(test_data, dest_path, "image/webp")
        assert url == "https://s3.fr-par.scw.cloud/test-bucket/photos/2026/vue.webp"
        mock_s3.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="photos/2026/vue.webp",
            Body=test_data,
            ContentType="image/webp",
        )

        # Test Exists
        mock_s3.head_object.return_value = {}
        exists = await s3_driver.exists(dest_path)
        assert exists is True

        # Test Read
        mock_body = MagicMock()
        mock_body.read.return_value = test_data
        mock_s3.get_object.return_value = {"Body": mock_body}
        read_data = await s3_driver.read(dest_path)
        assert read_data == test_data

        # Test Delete when exists
        deleted = await s3_driver.delete(dest_path)
        assert deleted is True
        mock_s3.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="photos/2026/vue.webp",
        )

        # Test Delete when does not exist
        mock_s3.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )
        deleted_non_existent = await s3_driver.delete("photos/unknown.webp")
        assert deleted_non_existent is False


def test_get_storage_driver_factory():
    driver = get_storage_driver()
    assert isinstance(driver, LocalStorageDriver)

