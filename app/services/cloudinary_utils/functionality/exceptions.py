"""
Custom exceptions for Cloudinary utilities
"""

class CloudinaryUtilsError(Exception):
    """Base exception for Cloudinary utilities"""
    pass

class ConfigurationError(CloudinaryUtilsError):
    """Raised when Cloudinary configuration is invalid or missing"""
    pass

class AssetNotFoundError(CloudinaryUtilsError):
    """Raised when a requested asset is not found"""
    pass

class UploadError(CloudinaryUtilsError):
    """Raised when upload operations fail"""
    pass

class TransformationError(CloudinaryUtilsError):
    """Raised when transformation operations fail"""
    pass

class AIAnalysisError(CloudinaryUtilsError):
    """Raised when AI analysis operations fail"""
    pass

class ArchiveError(CloudinaryUtilsError):
    """Raised when archive operations fail"""
    pass

class VideoProcessingError(CloudinaryUtilsError):
    """Raised when video processing operations fail"""
    pass

class PresetError(CloudinaryUtilsError):
    """Raised when upload preset operations fail"""
    pass

class BackupError(CloudinaryUtilsError):
    """Raised when backup operations fail"""
    pass

class BulkOperationError(CloudinaryUtilsError):
    """Raised when bulk operations fail"""
    pass

class QuotaExceededError(CloudinaryUtilsError):
    """Raised when Cloudinary quota is exceeded"""
    pass

class InvalidParameterError(CloudinaryUtilsError):
    """Raised when invalid parameters are provided"""
    pass