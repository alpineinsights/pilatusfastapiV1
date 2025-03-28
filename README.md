Financial Insights Chat App
A Streamlit application that allows users to chat with financial documents using Gemini AI and the Quartr API. The app fetches company financial documents, processes them, and uses AI to answer user queries about the selected company.

## Features

- Select a company from a list fetched from Supabase
- Fetch company financial documents from Quartr API using company IDs
- Convert transcript data to well-formatted PDFs
- Upload documents to Amazon S3
- Process user queries against the documents using Google's Gemini 2.0 Flash model
- Display AI-generated responses with source information

## Architecture
The application consists of several components:

- Streamlit Web Interface: Provides the user interface for company selection and chat
- Supabase Integration: Stores and retrieves company data with Quartr IDs
- Quartr API Integration: Fetches financial documents for the selected company using Quartr IDs
- Document Processing: Converts and standardizes documents (especially transcripts)
- S3 Storage: Stores processed documents for retrieval
- Gemini AI Integration: Analyzes documents and responds to user queries

## Prerequisites

- Python 3.9+
- AWS account with S3 access
- Quartr API key
- Google Gemini API key
- Supabase account with table for company universe

## Setup

1. Clone the repository
2. Install dependencies
```
pip install -r requirements.txt
```

3. Configure Streamlit secrets
   Create a `.streamlit/secrets.toml` file locally for development (never commit this to version control) or use the Streamlit Cloud secrets management. The secrets should include:
   ```
   AWS_ACCESS_KEY_ID = "your-aws-access-key"
   AWS_SECRET_ACCESS_KEY = "your-aws-secret-key"
   AWS_DEFAULT_REGION = "your-aws-region"
   S3_BUCKET_NAME = "your-s3-bucket"
   QUARTR_API_KEY = "your-quartr-api-key"
   GEMINI_API_KEY = "your-gemini-api-key"

   [connections.supabase]
   url = "your-supabase-url"
   token = "your-supabase-token"
   type = "sql"
   ```

4. Create an S3 bucket
   Create an S3 bucket to store the documents and ensure your AWS credentials have permission to write to it.

5. Set up Supabase
   Create a 'universe' table in Supabase with the following structure:
   - Name: Company name
   - ISIN: Company ISIN code (for backward compatibility)
   - QuartrID: Company ID from Quartr

## Project Structure
```
financial-insights-chat/
├── app.py                 # Main Streamlit application
├── supabase_client.py     # Supabase integration for company data
├── utils.py               # Utility classes for API, S3, and document processing
├── requirements.txt       # Python dependencies
├── .streamlit/            # Streamlit configuration
│   └── secrets.toml       # Local secrets file (not committed to repository)
└── README.md              # Project documentation
```

## Running the Application
```
streamlit run app.py
```

## How It Works

1. The user selects a company from the dropdown in the sidebar
2. The app fetches the company's Quartr ID from Supabase
3. The app fetches the latest financial documents from Quartr API using the company ID
4. Documents are processed and uploaded to S3
5. When the user asks a question, the app:
   - Downloads the relevant documents from S3
   - Sends them to Gemini AI along with the user's query
   - Displays the AI-generated response with source information

## Supabase Integration

The app uses Streamlit's native Supabase SQL connector to fetch company data. The Supabase table should include:
- Company names
- ISIN codes (for backward compatibility)
- Quartr IDs for each company

All API calls to Quartr are now made using Quartr IDs instead of ISIN codes for better compatibility with the Quartr API.
