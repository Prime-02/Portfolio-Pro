"""
Upload-focused Cloudinary utilities
"""
import cloudinary.uploader
from typing import List, Optional, Dict, Any
import asyncio
import base64
import logging

from .core import CloudinaryCore
from .models import (
    UploadResponse, 
    TransformationOptions, 
    BulkOperationResult,
    ResourceType
)
from .exceptions import UploadError, BulkOperationError

logger = logging.getLogger(__name__)

class CloudinaryUploader(CloudinaryCore):
    """
    Specialized class for upload operations
    """
    
    def upload_base64(
        self,
        base64_string: str,
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs
    ) -> UploadResponse:
        """
        Upload a base64 encoded file to Cloudinary
        
        Args:
            base64_string: Base64 encoded file data
            public_id: Custom public ID for the asset
            folder: Folder to organize assets
            tags: Tags for the asset
            transformation: Transformation options
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse with upload details
        """
        try:
            upload_params = {
                "resource_type": resource_type.value,
                **kwargs
            }
            
            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if tags:
                upload_params["tags"] = tags
            if transformation:
                upload_params["transformation"] = transformation.dict(exclude_none=True)
            
            # Ensure proper data URL format
            if not base64_string.startswith('data:'):
                base64_string = f"data:image/png;base64,{base64_string}"
            
            result = cloudinary.uploader.upload(base64_string, **upload_params)
            
            logger.info(f"Successfully uploaded base64 file: {result.get('public_id')}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Base64 upload error: {str(e)}")
            raise UploadError(f"Base64 upload failed: {str(e)}")

    async def upload_multiple_files(
        self,
        files: List,  # Can be UploadFile objects or file paths
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        max_concurrent: int = 5,
        **kwargs
    ) -> BulkOperationResult:
        """
        Upload multiple files to Cloudinary concurrently
        
        Args:
            files: List of file objects or paths
            folder: Folder to organize assets
            tags: Tags for the assets
            transformation: Transformation options
            resource_type: Type of resource
            max_concurrent: Maximum concurrent uploads
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with detailed results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def upload_single(file_item) -> Dict[str, Any]:
            async with semaphore:
                try:
                    if hasattr(file_item, 'read'):  # UploadFile object
                        result = await self.upload_file(
                            file=file_item,
                            folder=folder,
                            tags=tags,
                            transformation=transformation,
                            resource_type=resource_type,
                            **kwargs
                        )
                        return {
                            "file": getattr(file_item, 'filename', 'unknown'),
                            "status": "success",
                            "result": result.dict()
                        }
                    else:  # File path or URL
                        result = self.upload_from_url(
                            url=str(file_item),
                            folder=folder,
                            tags=tags,
                            transformation=transformation,
                            resource_type=resource_type,
                            **kwargs
                        )
                        return {
                            "file": str(file_item),
                            "status": "success", 
                            "result": result.dict()
                        }
                except Exception as e:
                    return {
                        "file": getattr(file_item, 'filename', str(file_item)),
                        "status": "failed",
                        "error": str(e)
                    }
        
        # Execute uploads concurrently
        tasks = [upload_single(file_item) for file_item in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        errors = []
        processed_results = []
        
        for result in results:
            if isinstance(result, Exception):
                failed += 1
                errors.append({"error": str(result)})
            else:
                processed_results.append(result)
                if result["status"] == "success":
                    successful += 1
                else:
                    failed += 1
                    errors.append(result)
        
        return BulkOperationResult(
            total_processed=len(files),
            successful=successful,
            failed=failed,
            results=processed_results,
            errors=errors
        )

    def upload_multiple_urls(
        self,
        urls: List[str],
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs
    ) -> BulkOperationResult:
        """
        Upload multiple files from URLs
        
        Args:
            urls: List of URLs to upload
            folder: Folder to organize assets
            tags: Tags for the assets
            transformation: Transformation options
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with detailed results
        """
        results = []
        successful = 0
        failed = 0
        errors = []
        
        for url in urls:
            try:
                result = self.upload_from_url(
                    url=url,
                    folder=folder,
                    tags=tags,
                    transformation=transformation,
                    resource_type=resource_type,
                    **kwargs
                )
                results.append({
                    "url": url,
                    "status": "success",
                    "result": result.dict()
                })
                successful += 1
                
            except Exception as e:
                error_info = {
                    "url": url,
                    "status": "failed",
                    "error": str(e)
                }
                results.append(error_info)
                errors.append(error_info)
                failed += 1
                logger.error(f"Failed to upload from URL {url}: {e}")
        
        return BulkOperationResult(
            total_processed=len(urls),
            successful=successful,
            failed=failed,
            results=results,
            errors=errors
        )

    def upload_with_eager_transformations(
        self,
        file_path_or_url: str,
        eager_transformations: List[TransformationOptions],
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs
    ) -> UploadResponse:
        """
        Upload file with eager transformations (pre-generate transformed versions)
        
        Args:
            file_path_or_url: File path or URL to upload
            eager_transformations: List of transformations to pre-generate
            public_id: Custom public ID
            folder: Folder to organize assets
            tags: Tags for the asset
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse with upload details including eager URLs
        """
        try:
            upload_params = {
                "resource_type": resource_type.value,
                "eager": [t.dict(exclude_none=True) for t in eager_transformations],
                **kwargs
            }
            
            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if tags:
                upload_params["tags"] = tags
            
            result = cloudinary.uploader.upload(file_path_or_url, **upload_params)
            
            logger.info(f"Uploaded with eager transformations: {result.get('public_id')}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Eager upload error: {str(e)}")
            raise UploadError(f"Eager upload failed: {str(e)}")

    def upload_with_auto_tagging(
        self,
        file_path_or_url: str,
        auto_tagging: float = 0.7,  # Confidence threshold
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        additional_tags: Optional[List[str]] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs
    ) -> UploadResponse:
        """
        Upload file with automatic AI-based tagging
        
        Args:
            file_path_or_url: File path or URL to upload
            auto_tagging: Confidence threshold for auto-tagging (0.0-1.0)
            public_id: Custom public ID
            folder: Folder to organize assets
            additional_tags: Additional manual tags
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse with upload details including auto-generated tags
        """
        try:
            upload_params = {
                "resource_type": resource_type.value,
                "auto_tagging": auto_tagging,
                **kwargs
            }
            
            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if additional_tags:
                upload_params["tags"] = additional_tags
            
            result = cloudinary.uploader.upload(file_path_or_url, **upload_params)
            
            logger.info(f"Uploaded with auto-tagging: {result.get('public_id')}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Auto-tagging upload error: {str(e)}")
            raise UploadError(f"Auto-tagging upload failed: {str(e)}")

    def upload_large_file(
        self,
        file_path: str,
        chunk_size: int = 20000000,  # 20MB chunks
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs
    ) -> UploadResponse:
        """
        Upload large files using chunked upload
        
        Args:
            file_path: Path to the large file
            chunk_size: Size of each chunk in bytes
            public_id: Custom public ID
            folder: Folder to organize assets
            tags: Tags for the asset
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse with upload details
        """
        try:
            upload_params = {
                "resource_type": resource_type.value,
                "chunk_size": chunk_size,
                **kwargs
            }
            
            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if tags:
                upload_params["tags"] = tags
            
            result = cloudinary.uploader.upload_large(file_path, **upload_params)
            
            logger.info(f"Large file uploaded: {result.get('public_id')}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Large file upload error: {str(e)}")
            raise UploadError(f"Large file upload failed: {str(e)}")

    def upload_with_preprocessing(
        self,
        file_path_or_data: str,
        preprocessing_steps: List[str],
        public_id: Optional[str] = None,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        resource_type: ResourceType = ResourceType.AUTO,
        **kwargs
    ) -> UploadResponse:
        """
        Upload file with preprocessing steps (like face detection, moderation)
        
        Args:
            file_path_or_data: File path, URL, or data to upload
            preprocessing_steps: List of preprocessing operations
            public_id: Custom public ID
            folder: Folder to organize assets
            tags: Tags for the asset
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse with upload details and preprocessing results
        """
        try:
            upload_params = {
                "resource_type": resource_type.value,
                **kwargs
            }
            
            # Add preprocessing options
            if "face_detection" in preprocessing_steps:
                upload_params["faces"] = True
            if "moderation" in preprocessing_steps:
                upload_params["moderation"] = "aws_rek"
            if "ocr" in preprocessing_steps:
                upload_params["ocr"] = "adv_ocr"
            if "categorization" in preprocessing_steps:
                upload_params["categorization"] = "aws_rek_tagging"
            
            if public_id:
                upload_params["public_id"] = public_id
            if folder:
                upload_params["folder"] = folder
            if tags:
                upload_params["tags"] = tags
            
            result = cloudinary.uploader.upload(file_path_or_data, **upload_params)
            
            logger.info(f"Uploaded with preprocessing: {result.get('public_id')}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Preprocessing upload error: {str(e)}")
            raise UploadError(f"Preprocessing upload failed: {str(e)}")