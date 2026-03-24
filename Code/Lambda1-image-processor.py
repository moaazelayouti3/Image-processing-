import json
import boto3
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import io
import os

# Initialize S3 client
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda function to resize and watermark images uploaded to S3
    Triggered by S3 PUT events
    """
   
    # Configuration - set these as environment variables in Lambda
    DESTINATION_BUCKET = os.environ.get('DESTINATION_BUCKET', 'resized-image-bucket-9965')
    RESIZE_WIDTH = int(os.environ.get('RESIZE_WIDTH', '800'))
    RESIZE_HEIGHT = int(os.environ.get('RESIZE_HEIGHT', '600'))
    QUALITY = int(os.environ.get('QUALITY', '85'))
    
    # Watermark configuration
    WATERMARK_TEXT = os.environ.get('WATERMARK_TEXT', 'By Moaaz-Elayouti')
    WATERMARK_OPACITY = int(os.environ.get('WATERMARK_OPACITY', '200'))  # 0-255
    WATERMARK_POSITION = os.environ.get('WATERMARK_POSITION', 'bottom-right')  # top-left, top-right, bottom-left, bottom-right, center
    WATERMARK_SIZE_RATIO = float(os.environ.get('WATERMARK_SIZE_RATIO', '0.3'))  # Relative to image width
   
    try:
        # Process each record in the event
        for record in event['Records']:
            # Get bucket and object key from the event
            source_bucket = record['s3']['bucket']['name']
            source_key = urllib.parse.unquote_plus(
                record['s3']['object']['key'],
                encoding='utf-8'
            )
           
            print(f"Processing image: {source_key} from bucket: {source_bucket}")
           
            # Skip if not an image file
            if not is_image_file(source_key):
                print(f"Skipping non-image file: {source_key}")
                continue
           
            # Download the image from S3
            try:
                response = s3.get_object(Bucket=source_bucket, Key=source_key)
                image_content = response['Body'].read()
            except Exception as e:
                print(f"Error downloading {source_key}: {str(e)}")
                continue
           
            # Process the image (resize and watermark)
            try:
                processed_image_content = process_image(
                    image_content,
                    RESIZE_WIDTH,
                    RESIZE_HEIGHT,
                    QUALITY,
                    WATERMARK_TEXT,
                    WATERMARK_OPACITY,
                    WATERMARK_POSITION,
                    WATERMARK_SIZE_RATIO
                )
            except Exception as e:
                print(f"Error processing {source_key}: {str(e)}")
                continue
           
            # Generate destination key
            destination_key = generate_destination_key(source_key)
           
            # Upload processed image to destination bucket
            try:
                s3.put_object(
                    Bucket=DESTINATION_BUCKET,
                    Key=destination_key,
                    Body=processed_image_content,
                    ContentType=get_content_type(source_key)
                )
                print(f"Successfully uploaded processed image: {destination_key}")
               
            except Exception as e:
                print(f"Error uploading {destination_key}: {str(e)}")
                continue
       
        return {
            'statusCode': 200,
            'body': json.dumps('Images processed successfully')
        }
       
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing images: {str(e)}')
        }

def is_image_file(file_key):
    """Check if the file is an image based on extension"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    return any(file_key.lower().endswith(ext) for ext in image_extensions)

def process_image(image_content, width, height, quality, watermark_text, opacity, position, size_ratio):
    """
    Resize and watermark image
    """
    # Open image from bytes
    with Image.open(io.BytesIO(image_content)) as img:
        # Convert RGBA to RGB if necessary (for JPEG)
        original_format = img.format
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
       
        # Resize image first
        resized_img = resize_image_content(img, width, height)
        
        # Add watermark
        watermarked_img = add_watermark(resized_img, watermark_text, opacity, position, size_ratio)
       
        # Save to bytes
        output_buffer = io.BytesIO()
       
        # Determine format based on original image
        format_map = {
            'JPEG': 'JPEG',
            'JPG': 'JPEG',
            'PNG': 'PNG',
            'GIF': 'GIF',
            'BMP': 'BMP',
            'WEBP': 'WEBP'
        }
       
        # Default to JPEG if format not recognized
        output_format = format_map.get(original_format, 'JPEG')
       
        if output_format == 'JPEG':
            watermarked_img.save(output_buffer, format=output_format, quality=quality, optimize=True)
        else:
            watermarked_img.save(output_buffer, format=output_format, optimize=True)
       
        return output_buffer.getvalue()

def resize_image_content(img, width, height):
    """
    Resize image while maintaining aspect ratio
    """
    # Calculate new dimensions maintaining aspect ratio
    original_width, original_height = img.size
    aspect_ratio = original_width / original_height
   
    if aspect_ratio > width / height:
        # Image is wider, fit to width
        new_width = width
        new_height = int(width / aspect_ratio)
    else:
        # Image is taller, fit to height
        new_height = height
        new_width = int(height * aspect_ratio)
   
    # Resize image
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

def add_watermark(img, watermark_text, opacity, position, size_ratio):
    """
    Add text watermark to image
    """
    # Create a copy of the image to work with
    watermarked = img.copy()
    
    # Create a transparent overlay for the watermark
    overlay = Image.new('RGBA', watermarked.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Calculate font size based on image width
    font_size = int(watermarked.size[0] * size_ratio)
    
    try:
        # Try to use a default font, fall back to basic font if not available
        font = ImageFont.load_default()
        # For better quality, you might want to include a TTF font file in your Lambda layer
        # font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    # Get text bounding box
    bbox = draw.textbbox((0, 0), watermark_text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position based on preference
    img_width, img_height = watermarked.size
    margin = 20
    
    position_map = {
        'top-left': (margin, margin),
        'top-right': (img_width - text_width - margin, margin),
        'bottom-left': (margin, img_height - text_height - margin),
        'bottom-right': (img_width - text_width - margin, img_height - text_height - margin),
        'center': ((img_width - text_width) // 2, (img_height - text_height) // 2)
    }
    
    x, y = position_map.get(position, position_map['bottom-right'])
    
    # Draw watermark text with specified opacity
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, opacity))
    
    # Composite the overlay onto the original image
    watermarked = Image.alpha_composite(watermarked.convert('RGBA'), overlay)
    
    # Convert back to RGB if needed
    if watermarked.mode == 'RGBA':
        background = Image.new('RGB', watermarked.size, (255, 255, 255))
        background.paste(watermarked, mask=watermarked.split()[-1])
        watermarked = background
    
    return watermarked

def add_image_watermark(img, watermark_img_content, opacity, position, scale_ratio):
    """
    Add image watermark to image (alternative method)
    This function can be used if you want to watermark with an image instead of text
    """
    # Create a copy of the image to work with
    watermarked = img.copy()
    
    # Open watermark image
    with Image.open(io.BytesIO(watermark_img_content)) as watermark:
        # Calculate watermark size
        img_width, img_height = watermarked.size
        wm_width = int(img_width * scale_ratio)
        wm_height = int(watermark.size[1] * (wm_width / watermark.size[0]))
        
        # Resize watermark
        watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)
        
        # Convert to RGBA for transparency
        if watermark.mode != 'RGBA':
            watermark = watermark.convert('RGBA')
        
        # Apply opacity
        watermark_with_opacity = Image.new('RGBA', watermark.size)
        for x in range(watermark.size[0]):
            for y in range(watermark.size[1]):
                r, g, b, a = watermark.getpixel((x, y))
                watermark_with_opacity.putpixel((x, y), (r, g, b, int(a * opacity / 255)))
        
        # Calculate position
        margin = 20
        position_map = {
            'top-left': (margin, margin),
            'top-right': (img_width - wm_width - margin, margin),
            'bottom-left': (margin, img_height - wm_height - margin),
            'bottom-right': (img_width - wm_width - margin, img_height - wm_height - margin),
            'center': ((img_width - wm_width) // 2, (img_height - wm_height) // 2)
        }
        
        x, y = position_map.get(position, position_map['bottom-right'])
        
        # Paste watermark
        if watermarked.mode != 'RGBA':
            watermarked = watermarked.convert('RGBA')
        watermarked.paste(watermark_with_opacity, (x, y), watermark_with_opacity)
    
    return watermarked

def generate_destination_key(source_key):
    """
    Generate destination key for processed image
    """
    # Split the key into path and filename
    path_parts = source_key.split('/')
    filename = path_parts[-1]
    directory = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ''
   
    # Add 'processed-' prefix to filename
    name, ext = os.path.splitext(filename)
    new_filename = f"processed-{name}{ext}"
   
    # Reconstruct the key
    if directory:
        return f"{directory}/{new_filename}"
    else:
        return new_filename

def get_content_type(file_key):
    """Get content type based on file extension"""
    content_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
   
    ext = os.path.splitext(file_key.lower())[1]
    return content_types.get(ext, 'application/octet-stream')