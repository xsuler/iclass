# iClass API

A Flask-based API for analyzing class schedules from images.

## Requirements

- Docker
- Docker Compose

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
```

## Running with Docker

### Build and start the application

```bash
docker-compose up -d
```

This will:
1. Build the Docker image
2. Start the container
3. Expose the API on port 8000

### Stop the application

```bash
docker-compose down
```

## API Endpoints

### Upload Image

```
POST /upload
```

Upload an image file for analysis. The API will extract class schedule information from the image.

**Request:**
- Form data with a file field named 'file'

**Response:**
```json
{
  "session_id": 0,
  "courses": [
    {
      "class_name": "Class Name",
      "class_date": "02.15 周六",
      "class_time": "10:00-11:00",
      "class_location": "Class Location",
      "class_instructor": "Class Instructor",
      "class_score_stars": 0
    }
  ]
}
```

## Development

If you want to run the application without Docker:

1. Install system dependencies:
   ```bash
   apt-get install -y tesseract-ocr tesseract-ocr-chi-sim libgl1-mesa-glx libglib2.0-0
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```