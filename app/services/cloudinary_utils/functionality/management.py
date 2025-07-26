"""
Asset management utilities for Cloudinary
"""
import cloudinary.api
import cloudinary.utils
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import logging

from .core import CloudinaryCore
from .models import (
    BackupOptions,
    BulkOperationResult,
    UsageReport,
    ArchiveOptions,
    ResourceType
)
from .exceptions import BackupError, BulkOperationError, CloudinaryUtilsError

logger = logging.getLogger(__name__)

class CloudinaryManager(CloudinaryCore):
    """
    Specialized class for asset management operations
    """
    
    def backup_assets(
        self,
        options: BackupOptions,
        **kwargs
    ) -> BulkOperationResult:
        """
        Create backup of assets by copying to backup folder
        
        Args:
            options: Backup configuration options
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with backup operation details
        """
        try:
            # List assets to backup
            list_params = {
                "resource_type": options.resource_type.value,
                "max_results": options.max_results,
                **kwargs
            }
            
            if options.prefix:
                list_params["prefix"] = options.prefix
            if options.tags:
                list_params["tags"] = True
            
            assets_response = cloudinary.api.resources(**list_params)
            assets = assets_response.get("resources", [])
            
            backup_results = []
            successful = 0
            failed = 0
            errors = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for asset in assets:
                original_public_id = asset["public_id"]
                backup_public_id = f"{options.backup_folder}/{timestamp}_{original_public_id}"
                
                try:
                    # Copy asset to backup location
                    result = cloudinary.uploader.upload(
                        asset["secure_url"],
                        public_id=backup_public_id,
                        resource_type=options.resource_type.value,
                        tags=["backup", f"backup_{timestamp}"]
                    )
                    
                    backup_results.append({
                        "original": original_public_id,
                        "backup": backup_public_id,
                        "status": "success",
                        "backup_url": result["secure_url"]
                    })
                    successful += 1
                    
                except Exception as e:
                    error_info = {
                        "original": original_public_id,
                        "backup": backup_public_id,
                        "status": "failed",
                        "error": str(e)
                    }
                    backup_results.append(error_info)
                    errors.append(error_info)
                    failed += 1
                    logger.error(f"Failed to backup {original_public_id}: {e}")
            
            logger.info(f"Backup completed: {successful} successful, {failed} failed")
            return BulkOperationResult(
                total_processed=len(assets),
                successful=successful,
                failed=failed,
                results=backup_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Backup operation error: {str(e)}")
            raise BackupError(f"Backup failed: {str(e)}")

    def restore_from_backup(
        self,
        backup_timestamp: str,
        backup_folder: str = "backups",
        target_folder: Optional[str] = None,
        overwrite: bool = False,
        **kwargs
    ) -> BulkOperationResult:
        """
        Restore assets from a specific backup
        
        Args:
            backup_timestamp: Timestamp of the backup to restore
            backup_folder: Folder containing backups
            target_folder: Target folder for restored assets
            overwrite: Whether to overwrite existing assets
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with restore operation details
        """
        try:
            # Find backup assets
            backup_prefix = f"{backup_folder}/{backup_timestamp}_"
            backup_assets = cloudinary.api.resources(
                prefix=backup_prefix,
                max_results=500,
                **kwargs
            )
            
            restore_results = []
            successful = 0
            failed = 0
            errors = []
            
            for asset in backup_assets.get("resources", []):
                backup_public_id = asset["public_id"]
                # Extract original public ID by removing backup prefix
                original_public_id = backup_public_id.replace(backup_prefix, "")
                
                if target_folder:
                    restore_public_id = f"{target_folder}/{original_public_id}"
                else:
                    restore_public_id = original_public_id
                
                try:
                    result = cloudinary.uploader.upload(
                        asset["secure_url"],
                        public_id=restore_public_id,
                        overwrite=overwrite,
                        tags=["restored", f"restored_{datetime.now().strftime('%Y%m%d_%H%M%S')}"]
                    )
                    
                    restore_results.append({
                        "backup": backup_public_id,
                        "restored": restore_public_id,
                        "status": "success",
                        "restored_url": result["secure_url"]
                    })
                    successful += 1
                    
                except Exception as e:
                    error_info = {
                        "backup": backup_public_id,
                        "restored": restore_public_id,
                        "status": "failed",
                        "error": str(e)
                    }
                    restore_results.append(error_info)
                    errors.append(error_info)
                    failed += 1
                    logger.error(f"Failed to restore {backup_public_id}: {e}")
            
            logger.info(f"Restore completed: {successful} successful, {failed} failed")
            return BulkOperationResult(
                total_processed=len(backup_assets.get("resources", [])),
                successful=successful,
                failed=failed,
                results=restore_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Restore operation error: {str(e)}")
            raise BackupError(f"Restore failed: {str(e)}")

    def cleanup_old_backups(
        self,
        backup_folder: str = "backups",
        days_to_keep: int = 30,
        **kwargs
    ) -> BulkOperationResult:
        """
        Clean up old backup files
        
        Args:
            backup_folder: Folder containing backups
            days_to_keep: Number of days to keep backups
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with cleanup operation details
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # List all backup assets
            backup_assets = cloudinary.api.resources(
                prefix=backup_folder,
                max_results=500,
                **kwargs
            )
            
            cleanup_results = []
            successful = 0
            failed = 0
            errors = []
            
            for asset in backup_assets.get("resources", []):
                # Parse timestamp from public_id
                try:
                    # Assuming format: backups/YYYYMMDD_HHMMSS_original_name
                    parts = asset["public_id"].split("/")
                    if len(parts) > 1:
                        timestamp_part = parts[1].split("_")[:2]  # Get date and time parts
                        if len(timestamp_part) == 2:
                            timestamp_str = f"{timestamp_part[0]}_{timestamp_part[1]}"
                            asset_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                            
                            if asset_date < cutoff_date:
                                # Delete old backup
                                result = self.delete_asset(
                                    public_id=asset["public_id"],
                                    resource_type=ResourceType(asset["resource_type"])
                                )
                                
                                cleanup_results.append({
                                    "public_id": asset["public_id"], 
                                    "date": asset_date.isoformat(),
                                    "status": "deleted" if result.get("result") == "ok" else "failed"
                                })
                                
                                if result.get("result") == "ok":
                                    successful += 1
                                else:
                                    failed += 1
                            else:
                                cleanup_results.append({
                                    "public_id": asset["public_id"],
                                    "date": asset_date.isoformat(), 
                                    "status": "kept"
                                })
                except Exception as e:
                    error_info = {
                        "public_id": asset["public_id"],
                        "status": "error",
                        "error": str(e)
                    }
                    cleanup_results.append(error_info)
                    errors.append(error_info)
                    failed += 1
                    logger.error(f"Failed to process backup {asset['public_id']}: {e}")
            
            logger.info(f"Cleanup completed: {successful} deleted, {failed} failed")
            return BulkOperationResult(
                total_processed=len(backup_assets.get("resources", [])),
                successful=successful,
                failed=failed,
                results=cleanup_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Cleanup operation error: {str(e)}")
            raise BackupError(f"Cleanup failed: {str(e)}")

    def create_archive(
        self,
        options: ArchiveOptions,
        **kwargs
    ) -> str:
        """
        Create an archive (ZIP/TAR) of assets
        
        Args:
            options: Archive configuration options
            **kwargs: Additional parameters
        
        Returns:
            Archive URL
        """
        try:
            archive_params = {
                "type": options.type.value,
                "mode": options.mode,
                "flatten_folders": options.flatten_folders,
                "keep_derived": options.keep_derived,
                **kwargs
            }
            
            if options.target_format:
                archive_params["target_format"] = options.target_format
            if options.tags:
                archive_params["tags"] = options.tags
            if options.public_ids:
                archive_params["public_ids"] = options.public_ids
            if options.prefixes:
                archive_params["prefixes"] = options.prefixes
            
            archive_url = cloudinary.utils.archive_url(**archive_params)
            
            logger.info(f"Created archive with type: {options.type.value}")
            return archive_url
            
        except Exception as e:
            logger.error(f"Archive creation error: {str(e)}")
            raise CloudinaryUtilsError(f"Archive creation failed: {str(e)}")

    def get_usage_report(self) -> UsageReport:
        """
        Get detailed account usage statistics
        
        Returns:
            UsageReport with usage data
        """
        try:
            usage_data = cloudinary.api.usage()
            logger.info("Retrieved usage report")
            return UsageReport(**usage_data)
            
        except Exception as e:
            logger.error(f"Usage report error: {str(e)}")
            raise CloudinaryUtilsError(f"Usage report failed: {str(e)}")

    def organize_assets_by_date(
        self,
        source_folder: Optional[str] = None,
        date_format: str = "%Y/%m",
        resource_type: ResourceType = ResourceType.IMAGE,
        dry_run: bool = False,
        **kwargs
    ) -> BulkOperationResult:
        """
        Organize assets into date-based folder structure
        
        Args:
            source_folder: Source folder to organize (None for root)
            date_format: Date format for folder structure
            resource_type: Type of resource to organize
            dry_run: If True, only show what would be moved
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with organization details
        """
        try:
            list_params = {
                "resource_type": resource_type.value,
                "max_results": 500,
                **kwargs
            }
            
            if source_folder:
                list_params["prefix"] = source_folder
            
            assets = cloudinary.api.resources(**list_params)
            
            organize_results = []
            successful = 0
            failed = 0
            errors = []
            
            for asset in assets.get("resources", []):
                try:
                    # Parse creation date
                    created_at = datetime.fromisoformat(
                        asset["created_at"].replace('Z', '+00:00')
                    )
                    
                    # Generate new folder path
                    date_folder = created_at.strftime(date_format)
                    original_public_id = asset["public_id"]
                    
                    # Extract filename from public_id
                    if "/" in original_public_id:
                        filename = original_public_id.split("/")[-1]
                    else:
                        filename = original_public_id
                    
                    new_public_id = f"{date_folder}/{filename}"
                    
                    if dry_run:
                        organize_results.append({
                            "original": original_public_id,
                            "new": new_public_id,
                            "status": "would_move",
                            "date": created_at.isoformat()
                        })
                        successful += 1
                    else:
                        # Rename/move the asset
                        result = cloudinary.uploader.rename(
                            original_public_id,
                            new_public_id,
                            resource_type=resource_type.value
                        )
                        
                        organize_results.append({
                            "original": original_public_id,
                            "new": new_public_id,
                            "status": "moved",
                            "date": created_at.isoformat()
                        })
                        successful += 1
                        
                except Exception as e:
                    error_info = {
                        "original": asset["public_id"],
                        "status": "failed",
                        "error": str(e)
                    }
                    organize_results.append(error_info)
                    errors.append(error_info)
                    failed += 1
                    logger.error(f"Failed to organize {asset['public_id']}: {e}")
            
            logger.info(f"Organization completed: {successful} processed, {failed} failed")
            return BulkOperationResult(
                total_processed=len(assets.get("resources", [])),
                successful=successful,
                failed=failed,
                results=organize_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Organization error: {str(e)}")
            raise BulkOperationError(f"Organization failed: {str(e)}")

    def find_duplicate_assets(
        self,
        resource_type: ResourceType = ResourceType.IMAGE,
        comparison_method: str = "phash",  # phash, colors, or bytes
        threshold: float = 0.9,
        **kwargs
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find potentially duplicate assets
        
        Args:
            resource_type: Type of resource to check
            comparison_method: Method for comparison
            threshold: Similarity threshold (0.0-1.0)
            **kwargs: Additional parameters
        
        Returns:
            Dictionary of potential duplicate groups
        """
        try:
            # Get all assets with metadata
            assets = cloudinary.api.resources(
                resource_type=resource_type.value,
                max_results=500,
                colors=True,
                phash=True,
                **kwargs
            )
            
            duplicates = {}
            processed_assets = []
            
            for asset in assets.get("resources", []):
                asset_data = {
                    "public_id": asset["public_id"],
                    "bytes": asset.get("bytes", 0),
                    "phash": asset.get("phash"),
                    "colors": asset.get("colors", []),
                    "url": asset["secure_url"]
                }
                
                # Find similar assets
                similar_assets = []
                for processed in processed_assets:
                    similarity = 0.0
                    
                    if comparison_method == "bytes" and asset_data["bytes"] == processed["bytes"]:
                        similarity = 1.0
                    elif comparison_method == "phash" and asset_data["phash"] and processed["phash"]:
                        # Simple phash comparison (in practice, use hamming distance)
                        if asset_data["phash"] == processed["phash"]:
                            similarity = 1.0
                    elif comparison_method == "colors" and asset_data["colors"] and processed["colors"]:
                        # Simple color comparison (in practice, use more sophisticated method)
                        common_colors = set(c[0] for c in asset_data["colors"][:5]) & \
                                      set(c[0] for c in processed["colors"][:5])
                        similarity = len(common_colors) / 5.0
                    
                    if similarity >= threshold:
                        similar_assets.append(processed)
                
                if similar_assets:
                    # Create or update duplicate group
                    group_key = f"group_{len(duplicates)}"
                    duplicates[group_key] = [asset_data] + similar_assets
                
                processed_assets.append(asset_data)
            
            logger.info(f"Found {len(duplicates)} potential duplicate groups")
            return duplicates
            
        except Exception as e:
            logger.error(f"Duplicate detection error: {str(e)}")
            raise CloudinaryUtilsError(f"Duplicate detection failed: {str(e)}")

    def bulk_update_tags(
        self,
        public_ids: List[str],
        tags_to_add: Optional[List[str]] = None,
        tags_to_remove: Optional[List[str]] = None,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> BulkOperationResult:
        """
        Bulk update tags for multiple assets
        
        Args:
            public_ids: List of public IDs to update
            tags_to_add: Tags to add
            tags_to_remove: Tags to remove
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with update operation details
        """
        try:
            update_results = []
            successful = 0
            failed = 0
            errors = []
            
            for public_id in public_ids:
                try:
                    update_params = {"resource_type": resource_type.value}
                    
                    # Get current tags
                    asset_info = cloudinary.api.resource(
                        public_id, 
                        resource_type=resource_type.value
                    )
                    current_tags = set(asset_info.get("tags", []))
                    
                    # Apply tag modifications
                    if tags_to_add:
                        current_tags.update(tags_to_add)
                    if tags_to_remove:
                        current_tags.difference_update(tags_to_remove)
                    
                    # Update tags
                    result = cloudinary.api.update(
                        public_id,
                        tags=list(current_tags),
                        **update_params
                    )
                    
                    update_results.append({
                        "public_id": public_id,
                        "status": "success",
                        "tags": list(current_tags)
                    })
                    successful += 1
                    
                except Exception as e:
                    error_info = {
                        "public_id": public_id,
                        "status": "failed",
                        "error": str(e)
                    }
                    update_results.append(error_info)
                    errors.append(error_info)
                    failed += 1
                    logger.error(f"Failed to update tags for {public_id}: {e}")
            
            logger.info(f"Bulk tag update completed: {successful} successful, {failed} failed")
            return BulkOperationResult(
                total_processed=len(public_ids),
                successful=successful,
                failed=failed,
                results=update_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Bulk tag update error: {str(e)}")
            raise BulkOperationError(f"Bulk tag update failed: {str(e)}")

    def get_folder_structure(
        self,
        max_depth: int = 5,
        include_asset_count: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get the folder structure of the Cloudinary account
        
        Args:
            max_depth: Maximum folder depth to traverse
            include_asset_count: Whether to include asset counts
            **kwargs: Additional parameters
        
        Returns:
            Dictionary representing folder structure
        """
        try:
            folders = cloudinary.api.subfolders("", max_results=500, **kwargs)
            folder_structure = {"root": {"subfolders": {}, "asset_count": 0}}
            
            def build_structure(folder_list, current_level=0):
                structure = {}
                
                for folder in folder_list.get("folders", []):
                    folder_name = folder["name"]
                    folder_path = folder["path"]
                    
                    structure[folder_name] = {
                        "path": folder_path,
                        "subfolders": {},
                        "asset_count": 0
                    }
                    
                    # Get asset count if requested
                    if include_asset_count:
                        try:
                            assets = cloudinary.api.resources(
                                prefix=folder_path,
                                max_results=1
                            )
                            structure[folder_name]["asset_count"] = len(assets.get("resources", []))
                        except Exception:
                            structure[folder_name]["asset_count"] = 0
                    
                    # Get subfolders if within depth limit
                    if current_level < max_depth:
                        try:
                            subfolders = cloudinary.api.subfolders(
                                folder_path, 
                                max_results=100
                            )
                            structure[folder_name]["subfolders"] = build_structure(
                                subfolders, 
                                current_level + 1
                            )
                        except Exception:
                            pass
                
                return structure
            
            folder_structure["root"]["subfolders"] = build_structure(folders)
            
            logger.info("Retrieved folder structure")
            return folder_structure
            
        except Exception as e:
            logger.error(f"Folder structure error: {str(e)}")
            raise CloudinaryUtilsError(f"Folder structure retrieval failed: {str(e)}")

    def cleanup_unused_transformations(
        self,
        resource_type: ResourceType = ResourceType.IMAGE,
        days_old: int = 30,
        dry_run: bool = True,
        **kwargs
    ) -> BulkOperationResult:
        """
        Clean up unused derived transformations
        
        Args:
            resource_type: Type of resource to clean
            days_old: Only clean transformations older than this
            dry_run: If True, only show what would be deleted
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with cleanup details
        """
        try:
            # Get all assets with derived resources
            assets = cloudinary.api.resources(
                resource_type=resource_type.value,
                max_results=500,
                derived=True,
                **kwargs
            )
            
            cleanup_results = []
            successful = 0
            failed = 0
            errors = []
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            for asset in assets.get("resources", []):
                derived_resources = asset.get("derived", [])
                
                for derived in derived_resources:
                    try:
                        # Check if derived resource is old enough
                        created_at = datetime.fromisoformat(
                            derived.get("created_at", asset["created_at"]).replace('Z', '+00:00')
                        )
                        
                        if created_at < cutoff_date:
                            derived_id = derived.get("id", "")
                            
                            if dry_run:
                                cleanup_results.append({
                                    "public_id": asset["public_id"],
                                    "derived_id": derived_id,
                                    "status": "would_delete",
                                    "created_at": created_at.isoformat()
                                })
                                successful += 1
                            else:
                                # Delete derived resource
                                result = cloudinary.api.delete_derived_resources([derived_id])
                                
                                cleanup_results.append({
                                    "public_id": asset["public_id"],
                                    "derived_id": derived_id,
                                    "status": "deleted",
                                    "created_at": created_at.isoformat()
                                })
                                successful += 1
                                
                    except Exception as e:
                        error_info = {
                            "public_id": asset["public_id"],
                            "derived_id": derived.get("id", "unknown"),
                            "status": "failed",
                            "error": str(e)
                        }
                        cleanup_results.append(error_info)
                        errors.append(error_info)
                        failed += 1
                        logger.error(f"Failed to clean derived resource: {e}")
            
            logger.info(f"Transformation cleanup: {successful} processed, {failed} failed")
            return BulkOperationResult(
                total_processed=len(cleanup_results),
                successful=successful,
                failed=failed,
                results=cleanup_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Transformation cleanup error: {str(e)}")
            raise BulkOperationError(f"Transformation cleanup failed: {str(e)}")

    def generate_asset_report(
        self,
        resource_type: ResourceType = ResourceType.IMAGE,
        include_metadata: bool = True,
        include_transformations: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate comprehensive asset report
        
        Args:
            resource_type: Type of resource to report on
            include_metadata: Whether to include detailed metadata
            include_transformations: Whether to include transformation data
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with comprehensive asset report
        """
        try:
            # Get basic asset data
            assets = cloudinary.api.resources(
                resource_type=resource_type.value,
                max_results=500,
                metadata=include_metadata,
                colors=include_metadata,
                derived=include_transformations,
                **kwargs
            )
            
            # Generate statistics
            total_assets = len(assets.get("resources", []))
            total_bytes = sum(asset.get("bytes", 0) for asset in assets.get("resources", []))
            
            # Analyze formats
            formats = {}
            folders = {}
            tags = {}
            sizes = {"small": 0, "medium": 0, "large": 0, "xlarge": 0}
            
            for asset in assets.get("resources", []):
                # Format analysis
                fmt = asset.get("format", "unknown")
                formats[fmt] = formats.get(fmt, 0) + 1
                
                # Folder analysis
                public_id = asset["public_id"]
                if "/" in public_id:
                    folder = public_id.split("/")[0]
                    folders[folder] = folders.get(folder, 0) + 1
                
                # Tag analysis
                for tag in asset.get("tags", []):
                    tags[tag] = tags.get(tag, 0) + 1
                
                # Size analysis
                bytes_size = asset.get("bytes", 0)
                if bytes_size < 100000:  # < 100KB
                    sizes["small"] += 1
                elif bytes_size < 1000000:  # < 1MB
                    sizes["medium"] += 1
                elif bytes_size < 10000000:  # < 10MB
                    sizes["large"] += 1
                else:
                    sizes["xlarge"] += 1
            
            report = {
                "summary": {
                    "total_assets": total_assets,
                    "total_bytes": total_bytes,
                    "total_size_mb": round(total_bytes / (1024 * 1024), 2),
                    "resource_type": resource_type.value,
                    "generated_at": datetime.now().isoformat()
                },
                "formats": dict(sorted(formats.items(), key=lambda x: x[1], reverse=True)),
                "folders": dict(sorted(folders.items(), key=lambda x: x[1], reverse=True)),
                "top_tags": dict(sorted(tags.items(), key=lambda x: x[1], reverse=True)[:20]),
                "size_distribution": sizes
            }
            
            if include_metadata:
                # Add more detailed analysis
                widths = [asset.get("width", 0) for asset in assets.get("resources", []) if asset.get("width")]
                heights = [asset.get("height", 0) for asset in assets.get("resources", []) if asset.get("height")]
                
                if widths:
                    report["dimensions"] = {
                        "avg_width": round(sum(widths) / len(widths)),
                        "max_width": max(widths),
                        "min_width": min(widths),
                        "avg_height": round(sum(heights) / len(heights)) if heights else 0,
                        "max_height": max(heights) if heights else 0,
                        "min_height": min(heights) if heights else 0
                    }
            
            logger.info(f"Generated asset report for {total_assets} assets")
            return report
            
        except Exception as e:
            logger.error(f"Asset report error: {str(e)}")
            raise CloudinaryUtilsError(f"Asset report generation failed: {str(e)}")

    def migrate_assets_between_folders(
        self,
        source_folder: str,
        target_folder: str,
        resource_type: ResourceType = ResourceType.IMAGE,
        preserve_structure: bool = True,
        dry_run: bool = False,
        **kwargs
    ) -> BulkOperationResult:
        """
        Migrate assets from one folder to another
        
        Args:
            source_folder: Source folder path
            target_folder: Target folder path
            resource_type: Type of resource to migrate
            preserve_structure: Whether to preserve subfolder structure
            dry_run: If True, only show what would be moved
            **kwargs: Additional parameters
        
        Returns:
            BulkOperationResult with migration details
        """
        try:
            # Get all assets in source folder
            assets = cloudinary.api.resources(
                prefix=source_folder,
                resource_type=resource_type.value,
                max_results=500,
                **kwargs
            )
            
            migration_results = []
            successful = 0
            failed = 0
            errors = []
            
            for asset in assets.get("resources", []):
                try:
                    original_public_id = asset["public_id"]
                    
                    if preserve_structure:
                        # Replace source folder with target folder
                        new_public_id = original_public_id.replace(
                            source_folder, 
                            target_folder, 
                            1
                        )
                    else:
                        # Move to target folder root
                        filename = original_public_id.split("/")[-1]
                        new_public_id = f"{target_folder}/{filename}"
                    
                    if dry_run:
                        migration_results.append({
                            "original": original_public_id,
                            "new": new_public_id,
                            "status": "would_move"
                        })
                        successful += 1
                    else:
                        # Rename/move the asset
                        result = cloudinary.uploader.rename(
                            original_public_id,
                            new_public_id,
                            resource_type=resource_type.value
                        )
                        
                        migration_results.append({
                            "original": original_public_id,
                            "new": new_public_id,
                            "status": "moved"
                        })
                        successful += 1
                        
                except Exception as e:
                    error_info = {
                        "original": asset["public_id"],
                        "status": "failed",
                        "error": str(e)
                    }
                    migration_results.append(error_info)
                    errors.append(error_info)
                    failed += 1
                    logger.error(f"Failed to migrate {asset['public_id']}: {e}")
            
            logger.info(f"Migration completed: {successful} moved, {failed} failed")
            return BulkOperationResult(
                total_processed=len(assets.get("resources", [])),
                successful=successful,
                failed=failed,
                results=migration_results,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Migration error: {str(e)}")
            raise BulkOperationError(f"Migration failed: {str(e)}")