"""
Core Cloudinary utilities with essential functionality
"""

import os
import cloudinary
import cloudinary.uploader
import cloudinary.utils
import cloudinary.api
from cloudinary.exceptions import Error as CloudinaryError
from typing import Optional, Dict, Any
from fastapi import HTTPException, UploadFile
import logging
from app.config import settings
from .models import (
    CloudinaryConfig,
    UploadResponse,
    TransformationOptions,
    AssetInfo,
    ResourceType,
)
from .exceptions import CloudinaryUtilsError, AssetNotFoundError, ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)


class CloudinaryCore:
    """Core Cloudinary functionality"""

    def __init__(self, config: CloudinaryConfig):
        """Initialize Cloudinary configuration"""
        if not all([config.cloud_name, config.api_key, config.api_secret]):
            raise ConfigurationError("Missing required Cloudinary configuration")

        self.config = config
        cloudinary.config(
            cloud_name=config.cloud_name,
            api_key=config.api_key,
            api_secret=config.api_secret,
            secure=config.secure,
        )
        logger.info(f"Cloudinary configured for cloud: {config.cloud_name}")

    @classmethod
    def from_env(cls) -> "CloudinaryCore":
        """Create CloudinaryCore instance from environment variables"""
        required_vars = [
            "CLOUDINARY_CLOUD_NAME",
            "CLOUDINARY_API_KEY",
            "CLOUDINARY_API_SECRET",
        ]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            raise ConfigurationError(
                f"Missing environment variables: {', '.join(missing_vars)}"
            )

        config = CloudinaryConfig(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
        return cls(config)

    async def upload_file(
        self,
        file: UploadFile,
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[list] = None,
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        overwrite: bool = False,
        unique_filename: bool = True,
        use_filename: bool = True,
        **kwargs,
    ) -> UploadResponse:
        """
        Upload a file to Cloudinary

        Args:
            file: FastAPI UploadFile object
            public_id: Custom public ID for the asset
            folder: Folder to organize assets
            tags: Tags for the asset
            transformation: Transformation options to apply during upload
            resource_type: Type of resource
            overwrite: Whether to overwrite existing asset
            unique_filename: Whether to use unique filename
            use_filename: Whether to use original filename
            **kwargs: Additional Cloudinary upload parameters

        Returns:
            UploadResponse with upload details
        """
        try:
            # Read file content
            file_content = await file.read()

            # Prepare upload parameters
            upload_params = {
                "resource_type": resource_type.value,
                "overwrite": overwrite,
                "unique_filename": unique_filename,
                "use_filename": use_filename,
                **kwargs,
            }

            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if tags:
                upload_params["tags"] = tags
            if transformation:
                upload_params["transformation"] = transformation.dict(exclude_none=True)

            # Upload to Cloudinary
            result = cloudinary.uploader.upload(file_content, **upload_params)

            logger.info(f"Successfully uploaded file: {result.get('public_id')}")
            return UploadResponse(**result)

        except CloudinaryError as e:
            logger.error(f"Cloudinary upload error: {str(e)}")
            raise CloudinaryUtilsError(f"Upload failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected upload error: {str(e)}")
            raise CloudinaryUtilsError(f"Upload failed: {str(e)}")

    def upload_from_url(
        self,
        url: str,
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[list] = None,
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs,
    ) -> UploadResponse:
        """
        Upload a file from URL to Cloudinary

        Args:
            url: URL of the file to upload
            public_id: Custom public ID for the asset
            folder: Folder to organize assets
            tags: Tags for the asset
            transformation: Transformation options to apply during upload
            resource_type: Type of resource
            **kwargs: Additional Cloudinary upload parameters

        Returns:
            UploadResponse with upload details
        """
        try:
            upload_params = {"resource_type": resource_type.value, **kwargs}

            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if tags:
                upload_params["tags"] = tags
            if transformation:
                upload_params["transformation"] = transformation.dict(exclude_none=True)

            result = cloudinary.uploader.upload(url, **upload_params)

            logger.info(f"Successfully uploaded from URL: {result.get('public_id')}")
            return UploadResponse(**result)

        except CloudinaryError as e:
            logger.error(f"Cloudinary URL upload error: {str(e)}")
            raise CloudinaryUtilsError(f"URL upload failed: {str(e)}")

    def get_url(
        self,
        public_id: str,
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.IMAGE,
        version: Optional[int] = None,
        secure: bool = True,
        **kwargs,
    ) -> str:
        """
        Generate URL for a Cloudinary asset

        Args:
            public_id: Public ID of the asset
            transformation: Transformation options
            resource_type: Type of resource
            version: Specific version of the asset
            secure: Whether to use HTTPS
            **kwargs: Additional URL parameters

        Returns:
            Generated URL string
        """
        try:
            url_params = {
                "resource_type": resource_type.value,
                "secure": secure,
                **kwargs,
            }

            if transformation:
                url_params["transformation"] = transformation.dict(exclude_none=True)
            if version:
                url_params["version"] = version

            url = cloudinary.utils.cloudinary_url(public_id, **url_params)[0]

            logger.debug(f"Generated URL for: {public_id}")
            return url

        except Exception as e:
            logger.error(f"Error generating URL: {str(e)}")
            raise CloudinaryUtilsError(f"URL generation failed: {str(e)}")

    def get_asset_info(
        self, public_id: str, resource_type: ResourceType = ResourceType.IMAGE
    ) -> AssetInfo:
        """
        Get detailed information about a Cloudinary asset

        Args:
            public_id: Public ID of the asset
            resource_type: Type of resource

        Returns:
            AssetInfo with detailed asset information
        """
        try:
            result = cloudinary.api.resource(
                public_id, resource_type=resource_type.value
            )
            logger.debug(f"Retrieved asset info for: {public_id}")
            return AssetInfo(**result)

        except CloudinaryError as e:
            if "NotFound" in str(e):
                raise AssetNotFoundError(f"Asset not found: {public_id}")
            logger.error(f"Error retrieving asset info: {str(e)}")
            raise CloudinaryUtilsError(f"Info retrieval failed: {str(e)}")

    def delete_asset(
        self,
        public_id: str,
        resource_type: ResourceType = ResourceType.IMAGE,
        invalidate: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Delete an asset from Cloudinary

        Args:
            public_id: Public ID of the asset to delete
            resource_type: Type of resource
            invalidate: Whether to invalidate CDN cache
            **kwargs: Additional deletion parameters

        Returns:
            Deletion result
        """
        try:
            result = cloudinary.uploader.destroy(
                public_id,
                resource_type=resource_type.value,
                invalidate=invalidate,
                **kwargs,
            )

            if result.get("result") == "ok":
                logger.info(f"Successfully deleted asset: {public_id}")
            else:
                logger.warning(f"Delete result for {public_id}: {result}")

            return result

        except CloudinaryError as e:
            logger.error(f"Error deleting asset: {str(e)}")
            raise CloudinaryUtilsError(f"Deletion failed: {str(e)}")

    def update_asset(
        self,
        public_id: str,
        tags: Optional[list] = None,
        context: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, str]] = None,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Update asset metadata, tags, or context

        Args:
            public_id: Public ID of the asset
            tags: New tags for the asset
            context: Context metadata
            metadata: Custom metadata
            resource_type: Type of resource
            **kwargs: Additional update parameters

        Returns:
            Updated asset information
        """
        try:
            update_params = {"resource_type": resource_type.value, **kwargs}

            if tags is not None:
                update_params["tags"] = tags
            if context:
                update_params["context"] = context
            if metadata:
                update_params["metadata"] = metadata

            result = cloudinary.api.update(public_id, **update_params)

            logger.info(f"Successfully updated asset: {public_id}")
            return result

        except CloudinaryError as e:
            logger.error(f"Error updating asset: {str(e)}")
            raise CloudinaryUtilsError(f"Update failed: {str(e)}")

    def validate_asset_exists(
        self, public_id: str, resource_type: ResourceType = ResourceType.IMAGE
    ) -> bool:
        """
        Check if an asset exists in Cloudinary

        Args:
            public_id: Public ID to check
            resource_type: Type of resource

        Returns:
            Boolean indicating if asset exists
        """
        try:
            cloudinary.api.resource(public_id, resource_type=resource_type.value)
            return True
        except CloudinaryError:
            return False

    def create_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Create a folder in Cloudinary

        Args:
            folder_path: Path of the folder to create

        Returns:
            Folder creation result
        """
        try:
            result = cloudinary.api.create_folder(folder_path)
            logger.info(f"Created folder: {folder_path}")
            return result

        except CloudinaryError as e:
            logger.error(f"Error creating folder: {str(e)}")
            raise CloudinaryUtilsError(f"Folder creation failed: {str(e)}")

    def delete_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Delete a folder from Cloudinary

        Args:
            folder_path: Path of the folder to delete

        Returns:
            Folder deletion result
        """
        try:
            result = cloudinary.api.delete_folder(folder_path)
            logger.info(f"Deleted folder: {folder_path}")
            return result

        except CloudinaryError as e:
            logger.error(f"Error deleting folder: {str(e)}")
            raise CloudinaryUtilsError(f"Folder deletion failed: {str(e)}")
