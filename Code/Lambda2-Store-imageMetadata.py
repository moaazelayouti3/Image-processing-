import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """
    Lambda function to receive image metadata from API Gateway
    and update DynamoDB table
    """
    
    # Configuration
    TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'Image-processing-Pics')
    
    # CORS headers for API Gateway
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization'
    }
    
    try:
        # Get the DynamoDB table
        table = dynamodb.Table(TABLE_NAME)
        
        # Handle CORS preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({'message': 'CORS preflight response'})
            }
        
        # Parse the request body
        if 'body' in event:
            if isinstance(event['body'], str):
                try:
                    body = json.loads(event['body'])
                except json.JSONDecodeError as e:
                    return create_error_response(400, f'Invalid JSON in request body: {str(e)}', cors_headers)
            else:
                body = event['body']
        else:
            return create_error_response(400, 'Request body is missing', cors_headers)
        
        # Determine the HTTP method
        http_method = event.get('httpMethod', 'POST')
        
        if http_method == 'POST':
            return handle_create_metadata(table, body, cors_headers)
        elif http_method == 'PUT':
            return handle_update_metadata(table, body, cors_headers)
        elif http_method == 'GET':
            return handle_get_metadata(table, event, cors_headers)
        elif http_method == 'DELETE':
            return handle_delete_metadata(table, event, cors_headers)
        else:
            return create_error_response(405, f'Method {http_method} not allowed', cors_headers)
            
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return create_error_response(500, f'Internal server error: {str(e)}', cors_headers)

def handle_create_metadata(table, body, cors_headers):
    """Handle POST request to create new image metadata"""
    try:
        # Validate required fields
        required_fields = ['ImageID', 'FileName']
        for field in required_fields:
            if field not in body:
                return create_error_response(400, f'Missing required field: {field}', cors_headers)
        
        # Prepare item for DynamoDB
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        item = {
            'ImageID': int(body['ImageID']),  # Ensure ImageID is a number
            'FileName': body['FileName'],
            'CreatedAt': timestamp,
            'UpdatedAt': timestamp
        }
        
        # Add optional fields if provided
        optional_fields = [
            'OriginalSize', 'ProcessedSize', 'Format', 'Width', 'Height',
            'S3Bucket', 'S3Key', 'ProcessedS3Key', 'Status', 'Tags',
            'Description', 'UploadedBy', 'ProcessingDuration', 'FileSize'
        ]
        
        for field in optional_fields:
            if field in body:
                # Convert numeric strings to Decimal for DynamoDB
                if field in ['OriginalSize', 'ProcessedSize', 'Width', 'Height', 'FileSize', 'ProcessingDuration']:
                    try:
                        item[field] = Decimal(str(body[field]))
                    except (ValueError, TypeError):
                        item[field] = body[field]
                else:
                    item[field] = body[field]
        
        # Put item in DynamoDB
        table.put_item(Item=item)
        
        print(f"Successfully created metadata for ImageID: {item['ImageID']}")
        
        return {
            'statusCode': 201,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Image metadata created successfully',
                'ImageID': item['ImageID'],
                'data': convert_decimals_to_float(item)
            }, default=str)
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ConditionalCheckFailedException':
            return create_error_response(409, 'Image metadata already exists', cors_headers)
        else:
            return create_error_response(500, f'DynamoDB error: {str(e)}', cors_headers)
    except ValueError as e:
        return create_error_response(400, f'Invalid ImageID format: {str(e)}', cors_headers)
    except Exception as e:
        return create_error_response(500, f'Error creating metadata: {str(e)}', cors_headers)

def handle_update_metadata(table, body, cors_headers):
    """Handle PUT request to update existing image metadata"""
    try:
        if 'ImageID' not in body:
            return create_error_response(400, 'ImageID is required for updates', cors_headers)
        
        image_id = int(body['ImageID'])
        
        # Check if item exists
        try:
            response = table.get_item(Key={'ImageID': image_id})
            if 'Item' not in response:
                return create_error_response(404, f'Image with ID {image_id} not found', cors_headers)
        except ClientError as e:
            return create_error_response(500, f'Error checking item existence: {str(e)}', cors_headers)
        
        # Build update expression
        update_expression = "SET UpdatedAt = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat() + 'Z'}
        
        updatable_fields = [
            'FileName', 'OriginalSize', 'ProcessedSize', 'Format', 'Width', 'Height',
            'S3Bucket', 'S3Key', 'ProcessedS3Key', 'Status', 'Tags',
            'Description', 'UploadedBy', 'ProcessingDuration', 'FileSize'
        ]
        
        for field in updatable_fields:
            if field in body:
                update_expression += f", {field} = :{field.lower()}"
                # Handle numeric fields
                if field in ['OriginalSize', 'ProcessedSize', 'Width', 'Height', 'FileSize', 'ProcessingDuration']:
                    try:
                        expression_values[f':{field.lower()}'] = Decimal(str(body[field]))
                    except (ValueError, TypeError):
                        expression_values[f':{field.lower()}'] = body[field]
                else:
                    expression_values[f':{field.lower()}'] = body[field]
        
        # Update item
        response = table.update_item(
            Key={'ImageID': image_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        print(f"Successfully updated metadata for ImageID: {image_id}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': 'Image metadata updated successfully',
                'ImageID': image_id,
                'data': convert_decimals_to_float(response['Attributes'])
            }, default=str)
        }
        
    except ValueError as e:
        return create_error_response(400, f'Invalid ImageID format: {str(e)}', cors_headers)
    except ClientError as e:
        return create_error_response(500, f'DynamoDB error: {str(e)}', cors_headers)
    except Exception as e:
        return create_error_response(500, f'Error updating metadata: {str(e)}', cors_headers)

def handle_get_metadata(table, event, cors_headers):
    """Handle GET request to retrieve image metadata"""
    try:
        # Check if ImageID is provided in path parameters
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        
        image_id = None
        if 'ImageID' in path_params:
            image_id = path_params['ImageID']
        elif 'ImageID' in query_params:
            image_id = query_params['ImageID']
        
        if image_id:
            # Get specific image metadata
            try:
                image_id = int(image_id)
                response = table.get_item(Key={'ImageID': image_id})
                
                if 'Item' not in response:
                    return create_error_response(404, f'Image with ID {image_id} not found', cors_headers)
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'message': 'Image metadata retrieved successfully',
                        'data': convert_decimals_to_float(response['Item'])
                    }, default=str)
                }
                
            except ValueError:
                return create_error_response(400, 'Invalid ImageID format', cors_headers)
        else:
            # Get all image metadata (with pagination)
            limit = int(query_params.get('limit', 50))
            last_key = query_params.get('lastKey')
            
            scan_params = {'Limit': limit}
            if last_key:
                try:
                    scan_params['ExclusiveStartKey'] = {'ImageID': int(last_key)}
                except ValueError:
                    return create_error_response(400, 'Invalid lastKey format', cors_headers)
            
            response = table.scan(**scan_params)
            
            result = {
                'message': 'Image metadata retrieved successfully',
                'data': [convert_decimals_to_float(item) for item in response.get('Items', [])],
                'count': len(response.get('Items', []))
            }
            
            if 'LastEvaluatedKey' in response:
                result['lastKey'] = response['LastEvaluatedKey']['ImageID']
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps(result, default=str)
            }
            
    except ClientError as e:
        return create_error_response(500, f'DynamoDB error: {str(e)}', cors_headers)
    except Exception as e:
        return create_error_response(500, f'Error retrieving metadata: {str(e)}', cors_headers)

def handle_delete_metadata(table, event, cors_headers):
    """Handle DELETE request to delete image metadata"""
    try:
        path_params = event.get('pathParameters', {}) or {}
        query_params = event.get('queryStringParameters', {}) or {}
        
        image_id = None
        if 'ImageID' in path_params:
            image_id = path_params['ImageID']
        elif 'ImageID' in query_params:
            image_id = query_params['ImageID']
        
        if not image_id:
            return create_error_response(400, 'ImageID is required for deletion', cors_headers)
        
        try:
            image_id = int(image_id)
        except ValueError:
            return create_error_response(400, 'Invalid ImageID format', cors_headers)
        
        # Check if item exists before deletion
        try:
            response = table.get_item(Key={'ImageID': image_id})
            if 'Item' not in response:
                return create_error_response(404, f'Image with ID {image_id} not found', cors_headers)
        except ClientError as e:
            return create_error_response(500, f'Error checking item existence: {str(e)}', cors_headers)
        
        # Delete the item
        table.delete_item(Key={'ImageID': image_id})
        
        print(f"Successfully deleted metadata for ImageID: {image_id}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'message': f'Image metadata for ID {image_id} deleted successfully',
                'ImageID': image_id
            })
        }
        
    except ClientError as e:
        return create_error_response(500, f'DynamoDB error: {str(e)}', cors_headers)
    except Exception as e:
        return create_error_response(500, f'Error deleting metadata: {str(e)}', cors_headers)

def convert_decimals_to_float(item):
    """Convert DynamoDB Decimal objects to float for JSON serialization"""
    if isinstance(item, dict):
        return {k: convert_decimals_to_float(v) for k, v in item.items()}
    elif isinstance(item, list):
        return [convert_decimals_to_float(i) for i in item]
    elif isinstance(item, Decimal):
        return float(item)
    else:
        return item

def create_error_response(status_code, message, headers):
    """Create standardized error response"""
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps({
            'error': True,
            'message': message,
            'statusCode': status_code
        })
    }