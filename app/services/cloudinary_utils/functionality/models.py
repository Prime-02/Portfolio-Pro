"""
Pydantic models for Cloudinary utilities
"""
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field
from enum import Enum

class ResourceType(str, Enum):
    """Cloudinary resource types"""
    AUTO = "auto"
    IMAGE = "image"
    VIDEO = "video"
    RAW = "raw"

class CropMode(str, Enum):
    """Cloudinary crop modes"""
    SCALE = "scale"
    FIT = "fit"
    FILL = "fill"
    CROP = "crop"
    THUMB = "thumb"
    PAD = "pad"
    LIMIT = "limit"
    MFIT = "mfit"
    MPAD = "mpad"

class GravityMode(str, Enum):
    """Cloudinary gravity modes"""
    CENTER = "center"
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"
    NORTHEAST = "northeast"
    NORTHWEST = "northwest"
    SOUTHEAST = "southeast"
    SOUTHWEST = "southwest"
    FACE = "face"
    FACES = "faces"
    AUTO = "auto"

class ArchiveType(str, Enum):
    """Archive types"""
    ZIP = "zip"
    TAR = "tar"

class CloudinaryConfig(BaseModel):
    """Cloudinary configuration"""
    cloud_name: str
    api_key: str
    api_secret: str
    secure: bool = True

class UploadResponse(BaseModel):
    """Response from Cloudinary upload operations"""
    public_id: str
    url: str
    secure_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    format: str
    resource_type: str
    bytes: int
    created_at: str
    version: int
    version_id: Optional[str] = None
    signature: str
    etag: Optional[str] = None
    folder: Optional[str] = None
    tags: Optional[List[str]] = None

class TransformationOptions(BaseModel):
    """Image transformation options"""
    # Basic dimensions
    width: Optional[int] = None
    height: Optional[int] = None
    crop: Optional[CropMode] = None
    
    # Quality and format
    quality: Optional[Union[str, int]] = None
    format: Optional[str] = None
    fetch_format: Optional[str] = None
    
    # Effects and filters
    effect: Optional[str] = None
    blur: Optional[Union[str, int]] = None
    sharpen: Optional[int] = None
    brightness: Optional[int] = None
    contrast: Optional[int] = None
    saturation: Optional[int] = None
    hue: Optional[int] = None
    gamma: Optional[float] = None
    
    # Positioning and rotation
    angle: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    gravity: Optional[GravityMode] = None
    
    # Visual styling
    radius: Optional[Union[str, int]] = None
    border: Optional[str] = None
    color: Optional[str] = None
    opacity: Optional[int] = None
    
    # Overlays and underlays
    overlay: Optional[str] = None
    underlay: Optional[str] = None
    
    # Flags and other options
    flags: Optional[str] = None

class VideoOptions(BaseModel):
    """Video-specific transformation options"""
    start_offset: Optional[Union[str, int]] = None
    end_offset: Optional[Union[str, int]] = None
    duration: Optional[Union[str, int]] = None
    fps: Optional[int] = None
    bit_rate: Optional[str] = None
    audio_codec: Optional[str] = None
    video_codec: Optional[str] = None
    keyframe_interval: Optional[float] = None
    streaming_profile: Optional[str] = None

class ArchiveOptions(BaseModel):
    """Options for creating archives"""
    type: ArchiveType = ArchiveType.ZIP
    mode: str = "create"
    target_format: Optional[str] = None
    flatten_folders: bool = False
    keep_derived: bool = False
    tags: Optional[List[str]] = None
    public_ids: Optional[List[str]] = None
    prefixes: Optional[List[str]] = None

class UploadPreset(BaseModel):
    """Upload preset configuration"""
    name: str
    unsigned: bool = False
    settings: Dict[str, Any] = Field(default_factory=dict)

class AIAnalysisResult(BaseModel):
    """AI analysis results"""
    moderation: Optional[Dict[str, Any]] = None
    ocr: Optional[Dict[str, Any]] = None
    face_detection: Optional[Dict[str, Any]] = None
    object_detection: Optional[Dict[str, Any]] = None
    categorization: Optional[Dict[str, Any]] = None
    auto_tagging: Optional[Dict[str, Any]] = None

class SearchOptions(BaseModel):
    """Search configuration options"""
    expression: str
    max_results: int = 10
    next_cursor: Optional[str] = None
    sort_by: Optional[str] = None
    aggregate: Optional[List[str]] = None
    with_field: Optional[List[str]] = None

class BackupOptions(BaseModel):
    """Backup configuration options"""
    backup_folder: str = "backups"
    resource_type: ResourceType = ResourceType.IMAGE
    max_results: int = 100
    include_derived: bool = False
    prefix: Optional[str] = None
    tags: Optional[List[str]] = None

class UsageReport(BaseModel):
    """Usage report data"""
    plan: str
    last_updated: str
    objects: Dict[str, Any]
    bandwidth: Dict[str, Any]
    storage: Dict[str, Any]
    requests: int
    resources: int
    derived_resources: int

class AssetInfo(BaseModel):
    """Extended asset information"""
    public_id: str
    format: str
    version: int
    resource_type: str
    type: str
    created_at: str
    uploaded_at: str
    bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    folder: Optional[str] = None
    tags: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    colors: Optional[List[List[Union[str, float]]]] = None
    predominant: Optional[Dict[str, Any]] = None
    url: str
    secure_url: str

class ResponsiveUrls(BaseModel):
    """Responsive URLs for different breakpoints"""
    urls: Dict[str, str]
    breakpoints: List[int]
    base_transformation: Optional[TransformationOptions] = None

class BulkOperationResult(BaseModel):
    """Result of bulk operations"""
    total_processed: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]] = Field(default_factory=list)

class WebhookNotification(BaseModel):
    """Cloudinary webhook notification structure"""
    notification_type: str
    timestamp: str
    request_id: str
    public_id: str
    version: int
    width: Optional[int] = None
    height: Optional[int] = None
    format: str
    resource_type: str
    created_at: str
    uploaded_at: str
    bytes: int
    url: str
    secure_url: str