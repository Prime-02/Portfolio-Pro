"""
Transformation-focused Cloudinary utilities
"""
import cloudinary.utils
import cloudinary.uploader
from typing import List, Dict, Optional, Any
import logging

from .core import CloudinaryCore
from .models import (
    TransformationOptions, 
    ResponsiveUrls, 
    UploadResponse,
    ResourceType
)
from .exceptions import TransformationError

logger = logging.getLogger(__name__)

class CloudinaryTransformer(CloudinaryCore):
    """
    Specialized class for image and video transformations
    """
    
    def generate_responsive_urls(
        self,
        public_id: str,
        breakpoints: List[int] = [320, 768, 1024, 1200, 1920],
        transformation: Optional[TransformationOptions] = None,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> ResponsiveUrls:
        """
        Generate responsive URLs for different screen sizes
        
        Args:
            public_id: Public ID of the asset
            breakpoints: List of width breakpoints
            transformation: Base transformation options
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            ResponsiveUrls object with URLs for each breakpoint
        """
        try:
            responsive_urls = {}
            
            for width in breakpoints:
                # Create transformation for this breakpoint
                if transformation:
                    breakpoint_transform = transformation.copy()
                    breakpoint_transform.width = width
                else:
                    breakpoint_transform = TransformationOptions(width=width)
                
                url = self.get_url(
                    public_id=public_id,
                    transformation=breakpoint_transform,
                    resource_type=resource_type,
                    **kwargs
                )
                responsive_urls[f"{width}w"] = url
            
            logger.info(f"Generated responsive URLs for: {public_id}")
            return ResponsiveUrls(
                urls=responsive_urls,
                breakpoints=breakpoints,
                base_transformation=transformation
            )
            
        except Exception as e:
            logger.error(f"Responsive URL generation error: {str(e)}")
            raise TransformationError(f"Responsive URL generation failed: {str(e)}")

    def create_transformation_chain(
        self,
        public_id: str,
        transformations: List[TransformationOptions],
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Create URL with chained transformations for complex image processing
        
        Args:
            public_id: Public ID of the asset
            transformations: List of transformation options to chain
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL with chained transformations applied
        """
        try:
            # Convert transformations to dictionary format
            transformation_chain = [t.dict(exclude_none=True) for t in transformations]
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation_chain,
                **kwargs
            )[0]
            
            logger.info(f"Generated chained transformation URL for: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Transformation chain error: {str(e)}")
            raise TransformationError(f"Transformation chain failed: {str(e)}")

    def create_sprite(
        self,
        public_ids: List[str],
        sprite_public_id: str,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        transformation: Optional[TransformationOptions] = None,
        **kwargs
    ) -> UploadResponse:
        """
        Create a sprite from multiple images
        
        Args:
            public_ids: List of public IDs to include in sprite
            sprite_public_id: Public ID for the generated sprite
            folder: Folder for the sprite
            tags: Tags for the sprite
            transformation: Transformation to apply to individual images
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse for the created sprite
        """
        try:
            sprite_params = {
                "public_id": sprite_public_id,
                **kwargs
            }
            
            if folder:
                sprite_params["folder"] = folder
            if tags:
                sprite_params["tags"] = tags
            if transformation:
                sprite_params["transformation"] = transformation.dict(exclude_none=True)
            
            # Create sprite using public IDs
            result = cloudinary.uploader.generate_sprite(
                tag=",".join(public_ids),
                **sprite_params
            )
            
            logger.info(f"Created sprite: {sprite_public_id}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Sprite creation error: {str(e)}")
            raise TransformationError(f"Sprite creation failed: {str(e)}")

    def apply_artistic_effects(
        self,
        public_id: str,
        effect_name: str,
        intensity: Optional[int] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Apply artistic effects to images
        
        Args:
            public_id: Public ID of the asset
            effect_name: Name of the artistic effect
            intensity: Effect intensity (if applicable)
            additional_params: Additional effect parameters
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL with artistic effect applied
        """
        try:
            effect_value = effect_name
            if intensity is not None:
                effect_value = f"{effect_name}:{intensity}"
            
            transformation = {"effect": effect_value}
            
            if additional_params:
                transformation.update(additional_params)
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Applied artistic effect '{effect_name}' to: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Artistic effect error: {str(e)}")
            raise TransformationError(f"Artistic effect failed: {str(e)}")

    def create_collage(
        self,
        public_ids: List[str],
        collage_public_id: str,
        width: int = 800,
        height: int = 600,
        layout: str = "auto",
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> UploadResponse:
        """
        Create a collage from multiple images
        
        Args:
            public_ids: List of public IDs to include in collage
            collage_public_id: Public ID for the generated collage
            width: Collage width
            height: Collage height
            layout: Collage layout strategy
            folder: Folder for the collage
            tags: Tags for the collage
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse for the created collage
        """
        try:
            # Create multi transformation for collage
            overlays = []
            for i, pid in enumerate(public_ids[1:], 1):  # Skip first image as base
                overlays.append({
                    "overlay": pid,
                    "width": width // 2,
                    "height": height // 2,
                    "crop": "fill",
                    "x": (i % 2) * (width // 2),
                    "y": (i // 2) * (height // 2)
                })
            
            # Base transformation with first image
            base_transform = {
                "width": width,
                "height": height,
                "crop": "fill"
            }
            
            transformation = [base_transform] + overlays
            
            # Upload the collage
            result = cloudinary.uploader.upload(
                public_ids[0],  # Use first image as base
                public_id=collage_public_id,
                folder=folder,
                tags=tags,
                transformation=transformation,
                **kwargs
            )
            
            logger.info(f"Created collage: {collage_public_id}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Collage creation error: {str(e)}")
            raise TransformationError(f"Collage creation failed: {str(e)}")

    def optimize_for_web(
        self,
        public_id: str,
        quality: str = "auto:best",
        format: str = "auto",
        progressive: bool = True,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Generate web-optimized URL with best practices
        
        Args:
            public_id: Public ID of the asset
            quality: Quality setting
            format: Format optimization
            progressive: Use progressive JPEG
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            Web-optimized URL
        """
        try:
            transformation = {
                "quality": quality,
                "fetch_format": format
            }
            
            if progressive and format in ["jpg", "jpeg", "auto"]:
                transformation["flags"] = "progressive"
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Generated web-optimized URL for: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Web optimization error: {str(e)}")
            raise TransformationError(f"Web optimization failed: {str(e)}")

    def create_animated_gif(
        self,
        public_ids: List[str],
        gif_public_id: str,
        delay: int = 200,  # milliseconds between frames
        loop: bool = True,
        folder: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> UploadResponse:
        """
        Create animated GIF from multiple images
        
        Args:
            public_ids: List of public IDs for animation frames
            gif_public_id: Public ID for the generated GIF
            delay: Delay between frames in milliseconds
            loop: Whether to loop the animation
            folder: Folder for the GIF
            tags: Tags for the GIF
            **kwargs: Additional parameters
        
        Returns:
            UploadResponse for the created animated GIF
        """
        try:
            # Create animation from multiple images
            transformation = {
                "flags": f"animated{'_loop' if loop else ''}",
                "delay": delay,
                "format": "gif"
            }
            
            # For now, use the multi method or create a video and convert
            # This is a simplified approach - actual implementation may vary
            result = cloudinary.uploader.multi(
                tag=",".join(public_ids),
                public_id=gif_public_id,
                folder=folder,
                tags=tags,
                transformation=transformation,
                **kwargs
            )
            
            logger.info(f"Created animated GIF: {gif_public_id}")
            return UploadResponse(**result)
            
        except Exception as e:
            logger.error(f"Animated GIF creation error: {str(e)}")
            raise TransformationError(f"Animated GIF creation failed: {str(e)}")

    def create_picture_in_picture(
        self,
        base_public_id: str,
        overlay_public_id: str,
        overlay_position: str = "bottom_right",
        overlay_size: str = "w_0.3,h_0.3",
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Create picture-in-picture effect
        
        Args:
            base_public_id: Public ID of the base image
            overlay_public_id: Public ID of the overlay image
            overlay_position: Position of the overlay (gravity)
            overlay_size: Size of the overlay
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL with picture-in-picture effect
        """
        try:
            transformation = {
                "overlay": overlay_public_id,
                "gravity": overlay_position,
                "transformation": overlay_size
            }
            
            url = cloudinary.utils.cloudinary_url(
                base_public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Created picture-in-picture for: {base_public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Picture-in-picture error: {str(e)}")
            raise TransformationError(f"Picture-in-picture failed: {str(e)}")

    def batch_transform_urls(
        self,
        public_ids: List[str],
        transformation: TransformationOptions,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> Dict[str, str]:
        """
        Generate transformed URLs for multiple assets
        
        Args:
            public_ids: List of public IDs to transform
            transformation: Transformation to apply to all assets
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            Dictionary mapping public IDs to transformed URLs
        """
        try:
            transformed_urls = {}
            
            for public_id in public_ids:
                url = self.get_url(
                    public_id=public_id,
                    transformation=transformation,
                    resource_type=resource_type,
                    **kwargs
                )
                transformed_urls[public_id] = url
            
            logger.info(f"Generated {len(transformed_urls)} transformed URLs")
            return transformed_urls
            
        except Exception as e:
            logger.error(f"Batch transformation error: {str(e)}")
            raise TransformationError(f"Batch transformation failed: {str(e)}")

    def create_watermark(
        self,
        public_id: str,
        watermark_text: str,
        position: str = "bottom_right",
        opacity: int = 50,
        font_size: int = 36,
        font_color: str = "white",
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Add text watermark to image
        
        Args:
            public_id: Public ID of the asset
            watermark_text: Text for watermark
            position: Position of watermark (gravity)
            opacity: Watermark opacity (0-100)
            font_size: Font size for watermark
            font_color: Font color for watermark
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL with watermark applied
        """
        try:
            transformation = {
                "overlay": {
                    "text": watermark_text,
                    "font_size": font_size,
                    "font_color": font_color
                },
                "gravity": position,
                "opacity": opacity
            }
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Added watermark to: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Watermark error: {str(e)}")
            raise TransformationError(f"Watermark failed: {str(e)}")

    def create_thumbnail_grid(
        self,
        public_ids: List[str],
        grid_width: int = 4,
        thumbnail_size: int = 150,
        spacing: int = 10,
        background_color: str = "white",
        **kwargs
    ) -> str:
        """
        Create a grid of thumbnails
        
        Args:
            public_ids: List of public IDs for thumbnails
            grid_width: Number of thumbnails per row
            thumbnail_size: Size of each thumbnail
            spacing: Spacing between thumbnails
            background_color: Background color of the grid
            **kwargs: Additional parameters
        
        Returns:
            URL of the generated thumbnail grid
        """
        try:
            rows = (len(public_ids) + grid_width - 1) // grid_width
            canvas_width = grid_width * thumbnail_size + (grid_width - 1) * spacing
            canvas_height = rows * thumbnail_size + (rows - 1) * spacing
            
            # Start with a colored background
            transformation = [{
                "width": canvas_width,
                "height": canvas_height,
                "crop": "pad",
                "background": background_color
            }]
            
            # Add each thumbnail as an overlay
            for i, public_id in enumerate(public_ids):
                row = i // grid_width
                col = i % grid_width
                
                x_pos = col * (thumbnail_size + spacing)
                y_pos = row * (thumbnail_size + spacing)
                
                overlay_transform = {
                    "overlay": public_id,
                    "width": thumbnail_size,
                    "height": thumbnail_size,
                    "crop": "fill",
                    "x": x_pos,
                    "y": y_pos,
                    "flags": "relative"
                }
                transformation.append(overlay_transform)
            
            # Use the first image as base and apply transformations
            url = cloudinary.utils.cloudinary_url(
                public_ids[0] if public_ids else "sample",
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Created thumbnail grid with {len(public_ids)} images")
            return url
            
        except Exception as e:
            logger.error(f"Thumbnail grid error: {str(e)}")
            raise TransformationError(f"Thumbnail grid creation failed: {str(e)}")

    def apply_instagram_filter(
        self,
        public_id: str,
        filter_name: str,
        intensity: int = 100,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Apply Instagram-like filters to images
        
        Args:
            public_id: Public ID of the asset
            filter_name: Name of the filter (vintage, sepia, etc.)
            intensity: Filter intensity (0-100)
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL with Instagram filter applied
        """
        try:
            filter_effects = {
                "vintage": f"sepia:{intensity},saturation:-30,brightness:10",
                "sepia": f"sepia:{intensity}",
                "noir": f"grayscale,contrast:20,brightness:-10",
                "warm": f"hue:10,saturation:20,brightness:5",
                "cool": f"hue:-10,saturation:15,brightness:5",
                "vivid": f"saturation:40,contrast:15",
                "muted": f"saturation:-20,brightness:5",
                "dramatic": f"contrast:30,saturation:20,brightness:-5"
            }
            
            effect = filter_effects.get(filter_name.lower(), f"{filter_name}:{intensity}")
            
            transformation = {"effect": effect}
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Applied {filter_name} filter to: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Instagram filter error: {str(e)}")
            raise TransformationError(f"Instagram filter failed: {str(e)}")

    def create_smart_crop_variants(
        self,
        public_id: str,
        crop_ratios: List[str] = ["1:1", "16:9", "4:3", "3:2"],
        size: int = 400,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> Dict[str, str]:
        """
        Create smart crop variants for different aspect ratios
        
        Args:
            public_id: Public ID of the asset
            crop_ratios: List of aspect ratios to generate
            size: Base size for cropping
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            Dictionary mapping aspect ratios to URLs
        """
        try:
            crop_variants = {}
            
            for ratio in crop_ratios:
                if ":" in ratio:
                    width_ratio, height_ratio = map(int, ratio.split(":"))
                    width = size
                    height = int(size * height_ratio / width_ratio)
                else:
                    width = height = size
                
                transformation = TransformationOptions(
                    width=width,
                    height=height,
                    crop="fill",
                    gravity="auto"
                )
                
                url = self.get_url(
                    public_id=public_id,
                    transformation=transformation,
                    resource_type=resource_type,
                    **kwargs
                )
                
                crop_variants[ratio] = url
            
            logger.info(f"Created smart crop variants for: {public_id}")
            return crop_variants
            
        except Exception as e:
            logger.error(f"Smart crop variants error: {str(e)}")
            raise TransformationError(f"Smart crop variants failed: {str(e)}")

    def create_progressive_jpeg(
        self,
        public_id: str,
        quality: int = 80,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Create progressive JPEG for better loading experience
        
        Args:
            public_id: Public ID of the asset
            quality: JPEG quality (0-100)
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL with progressive JPEG format
        """
        try:
            transformation = {
                "quality": quality,
                "format": "jpg",
                "flags": "progressive"
            }
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Created progressive JPEG for: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Progressive JPEG error: {str(e)}")
            raise TransformationError(f"Progressive JPEG creation failed: {str(e)}")

    def create_lazy_loading_placeholder(
        self,
        public_id: str,
        blur_intensity: int = 400,
        quality: int = 30,
        width: int = 100,
        resource_type: ResourceType = ResourceType.IMAGE,
        **kwargs
    ) -> str:
        """
        Create low-quality placeholder for lazy loading
        
        Args:
            public_id: Public ID of the asset
            blur_intensity: Blur effect intensity
            quality: Image quality for placeholder
            width: Width of placeholder
            resource_type: Type of resource
            **kwargs: Additional parameters
        
        Returns:
            URL for lazy loading placeholder
        """
        try:
            transformation = {
                "width": width,
                "quality": quality,
                "effect": f"blur:{blur_intensity}",
                "format": "jpg"
            }
            
            url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type.value,
                transformation=transformation,
                **kwargs
            )[0]
            
            logger.info(f"Created lazy loading placeholder for: {public_id}")
            return url
            
        except Exception as e:
            logger.error(f"Lazy loading placeholder error: {str(e)}")
            raise TransformationError(f"Lazy loading placeholder failed: {str(e)}")