# Serverless Image Upload & Resize Pipeline on AWS

This project implements a serverless architecture for uploading and processing images using **AWS API Gateway, S3, and Lambda**.  
The workflow allows users to upload an image via API Gateway, which stores the image in a **Source S3 Bucket**. A **Lambda function** is then triggered to resize the image and store it into a **Destination S3 Bucket**.

---

## 📌 Architecture

<img width="1536" height="1024" alt="image" src="https://github.com/ahmed0223/Image-Processing/blob/main/image-processing-architecture.png" />


1. **Web Application** uploads image via **API Gateway**.
2. **API Gateway** uploads the original image to the **Source S3 Bucket** (via signed URL or direct integration).
3. **S3 Event Trigger** activates a **Lambda Function** whenever a new object is created in the **Source Bucket**.
4. **Lambda Function** processes the image (resize, compress, etc.).
5. The processed image is uploaded to the **Destination S3 Bucket**.

---

## 🛠️ AWS Components

- **Amazon API Gateway**  
  - Acts as the entry point for client applications.  
  - Provides a secure REST API endpoint for uploading images.  
  - Issues a **pre-signed S3 URL** to allow direct upload into the Source Bucket.

- **Amazon S3 (Source Bucket)**  
  - Stores the original uploaded images.  
  - Configured with an event notification to trigger Lambda on `s3:ObjectCreated`.

- **AWS Lambda**  
  - Triggered by Source S3 Bucket events.  
  - Downloads the uploaded image, resizes it using libraries like **Pillow (Python)** or **Sharp (Node.js)**.  
  - Uploads the resized image to the Destination Bucket.

- **Amazon S3 (Destination Bucket)**  
  - Stores the resized/processed images.  
  - Can be configured with lifecycle policies, CloudFront CDN, or downstream integrations.

---

## 🔐 IAM Roles & Permissions

### API Gateway Execution Role
- Required to allow uploading objects to the Source Bucket.
```json
{
  "Effect": "Allow",
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::source-bucket-name/*"
}
