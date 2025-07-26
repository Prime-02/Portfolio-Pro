"""
Cloudinary utilities package

This package provides a comprehensive set of utilities for working with Cloudinary,
organized into focused modules for better maintainability and ease of use.
"""

from .functionality.core import CloudinaryCore
from .functionality.models import (
    CloudinaryConfig,
    UploadResponse,
    TransformationOptions,
    VideoOptions,
    ArchiveOptions,
    UploadPreset,
    AIAnalysisResult,
    SearchOptions,
    BackupOptions,
    UsageReport,
    AssetInfo,
    ResponsiveUrls,
    BulkOperationResult,
    ResourceType,
    CropMode,
    GravityMode,
    ArchiveType,
)
from .functionality.exceptions import (
    CloudinaryUtilsError,
    ConfigurationError,
    AssetNotFoundError,
    UploadError,
    TransformationError,
    AIAnalysisError,
    ArchiveError,
    VideoProcessingError,
    PresetError,
    BackupError,
    BulkOperationError,
    QuotaExceededError,
    InvalidParameterError,
)

# Import specialized utilities (these would be implemented in their respective files)
try:
    from .functionality.upload import CloudinaryUploader
except ImportError:
    CloudinaryUploader = None

try:
    from .functionality.transformation import CloudinaryTransformer
except ImportError:
    CloudinaryTransformer = None

try:
    from .functionality.ai_analysis import CloudinaryAI
except ImportError:
    CloudinaryAI = None

try:
    from .functionality.management import CloudinaryManager
except ImportError:
    CloudinaryManager = None

try:
    from .functionality.video import CloudinaryVideo
except ImportError:
    CloudinaryVideo = None

try:
    from .functionality.presets import CloudinaryPresets
except ImportError:
    CloudinaryPresets = None


# Main unified class that combines all functionality
class CloudinaryUtils(CloudinaryCore):
    """
    Unified Cloudinary utilities class that combines all functionality.

    This class inherits from CloudinaryCore and adds methods from all
    specialized modules, providing a single interface for all operations.
    """

    def __init__(self, config: CloudinaryConfig):
        super().__init__(config)

        # Initialize specialized handlers if available
        if CloudinaryUploader:
            self._uploader = CloudinaryUploader(config)
        if CloudinaryTransformer:
            self._transformer = CloudinaryTransformer(config)
        if CloudinaryAI:
            self._ai = CloudinaryAI(config)
        if CloudinaryManager:
            self._manager = CloudinaryManager(config)
        if CloudinaryVideo:
            self._video = CloudinaryVideo(config)
        if CloudinaryPresets:
            self._presets = CloudinaryPresets(config)

    # Delegate methods to specialized handlers
    def __getattr__(self, name):
        """
        Delegate method calls to appropriate specialized handlers
        """
        # Try each handler in order
        handlers = [
            getattr(self, "_uploader", None),
            getattr(self, "_transformer", None),
            getattr(self, "_ai", None),
            getattr(self, "_manager", None),
            getattr(self, "_video", None),
            getattr(self, "_presets", None),
        ]

        for handler in handlers:
            if handler and hasattr(handler, name):
                return getattr(handler, name)

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )


# Version information
__version__ = "2.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Package metadata
__all__ = [
    # Main classes
    "CloudinaryUtils",
    "CloudinaryCore",
    # Specialized classes
    "CloudinaryUploader",
    "CloudinaryTransformer",
    "CloudinaryAI",
    "CloudinaryManager",
    "CloudinaryVideo",
    "CloudinaryPresets",
    # Models
    "CloudinaryConfig",
    "UploadResponse",
    "TransformationOptions",
    "VideoOptions",
    "ArchiveOptions",
    "UploadPreset",
    "AIAnalysisResult",
    "SearchOptions",
    "BackupOptions",
    "UsageReport",
    "AssetInfo",
    "ResponsiveUrls",
    "BulkOperationResult",
    # Enums
    "ResourceType",
    "CropMode",
    "GravityMode",
    "ArchiveType",
    # Exceptions
    "CloudinaryUtilsError",
    "ConfigurationError",
    "AssetNotFoundError",
    "UploadError",
    "TransformationError",
    "AIAnalysisError",
    "ArchiveError",
    "VideoProcessingError",
    "PresetError",
    "BackupError",
    "BulkOperationError",
    "QuotaExceededError",
    "InvalidParameterError",
]


# Convenience functions for quick setup
def setup_from_env():
    """
    Quick setup function to create CloudinaryUtils from environment variables

    Returns:
        CloudinaryUtils: Configured instance
    """
    return CloudinaryUtils.from_env()


def create_uploader_only():
    """
    Create only the uploader component for lightweight usage

    Returns:
        CloudinaryUploader: Upload-focused instance
    """
    if CloudinaryUploader:
        return CloudinaryUploader.from_env()
    raise ImportError("CloudinaryUploader not available")


def create_transformer_only():
    """
    Create only the transformer component for image processing

    Returns:
        CloudinaryTransformer: Transformation-focused instance
    """
    if CloudinaryTransformer:
        return CloudinaryTransformer.from_env()
    raise ImportError("CloudinaryTransformer not available")
