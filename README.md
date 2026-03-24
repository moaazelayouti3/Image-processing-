# Serverless Image Upload & Resize Pipeline on AWS

This project uses a **serverless architecture** to upload and process images using **AWS API Gateway**, **Amazon S3**, and **AWS Lambda**.

Users upload images through **API Gateway**, where they are stored in a **Source S3 Bucket**. An **AWS Lambda function** is automatically triggered to resize the images and store the processed versions in a **Destination S3 Bucket**.

---

## 📌 Architecture

<img width="1536" height="1024" alt="image" src="https://github.com/moaazelayouti3/Image-processing-/blob/main/image-processing-architecture.png" />



1. **Web Application** uploads an image through **API Gateway**.
2. The image is stored in the **Source S3 Bucket**.
3. An **S3 event** triggers a **Lambda function**.
4. **Lambda** processes the image.
5. The processed image is saved in the **Destination S3 Bucket**.

---

## 🛠️ AWS Components

- **Amazon API Gateway**  
  - Serves as the main entry point for client requests.  
  - Exposes a secure REST API for image uploads.  
  - Generates **pre-signed S3 URLs** to enable direct uploads to the Source Bucket.

- **Amazon S3 (Source Bucket)**  
  - Stores the original images uploaded by users.  
  - Configured to trigger AWS Lambda on `s3:ObjectCreated` events.

- **AWS Lambda**  
  - Invoked automatically when new objects are added to the Source Bucket.  
  - Processes images (resize, optimize, etc.) using libraries such as **Pillow (Python)** or **Sharp (Node.js)**.  
  - Saves the processed images to the Destination Bucket.

- **Amazon S3 (Destination Bucket)**  
  - Stores the processed and resized images.  
  - Can be extended with lifecycle rules, CloudFront CDN, or other integrations.

---

## 🔐 IAM Roles & Permissions

### API Gateway Execution Role
- Grants API Gateway permission to upload objects to the Source S3 Bucket.

```json
{
  "Effect": "Allow",
  "Action": "s3:PutObject",
  "Resource": "arn:aws:s3:::source-bucket-name/*"
}
