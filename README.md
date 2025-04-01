# Financial Insights Chat App

A Streamlit application that enables financial professionals to chat with financial documents using a multi-LLM pipeline. The app fetches company financial documents from the Quartr API, processes them, gets real-time web information, and uses advanced AI models to answer user queries about the selected company.

## Features

- Select a company from a comprehensive list fetched from Supabase
- Fetch financial documents from Quartr API using company IDs
- Convert transcript data to well-formatted PDFs
- Upload and retrieve documents from Amazon S3
- **Conversational Context**: Maintain conversation history for follow-up questions
- Three-step LLM chain for comprehensive answers:
  1. **Document Analysis**: Gemini 2.0 Flash analyzes company documents
  2. **Web Search**: Perplexity API fetches current information
  3. **Final Synthesis**: Claude 3.7 Sonnet combines both sources for comprehensive answers
- Parallel processing for optimal performance
- Display AI-generated responses with source links

## Architecture

The application uses a sophisticated architecture with multiple components:

- **Streamlit Web Interface**: User interface for company selection and chat
- **Supabase Integration**: Stores and retrieves company data with Quartr IDs
- **Quartr API Integration**: Fetches financial documents for selected companies
- **Document Processing**: Converts and standardizes documents (especially transcripts)
- **S3 Storage**: Stores processed documents for retrieval
- **Multi-LLM Pipeline**:
  - **Gemini AI**: Analyzes company documents 
  - **Perplexity API**: Searches the web for current information
  - **Claude AI**: Synthesizes all information into comprehensive responses
- **Asynchronous Processing**: Runs tasks in parallel for optimal performance
- **Conversation Management**: Maintains context for follow-up questions

## Technical Implementation

### Multi-LLM Chain
The application implements a sophisticated multi-LLM chain:

1. **First Stage** (Runs in Parallel):
   - **Gemini 2.0 Flash**: Analyzes company documents retrieved from S3
   - **Perplexity API**: Simultaneously searches the web for the most current information, with specific research context about the company

2. **Second Stage**:
   - **Claude 3.7 Sonnet**: Synthesizes outputs from both sources, providing a comprehensive answer that combines historical company documents with current information

### Conversation Management
- Maintains context of previous exchanges for natural follow-up questions
- Each LLM in the chain receives relevant conversation history
- Thread-safe implementation of context sharing between parallel processes
- Context pruning to prevent token overflow (limits to last 5 exchanges)
- Company-specific conversation tracking (resets when switching companies)

### Performance Optimization
- Perplexity API call starts immediately when a user query is submitted
- Document processing and Gemini analysis run concurrently
- Asynchronous operations with proper thread management
- Detailed timing metrics for performance monitoring

## Prerequisites

- Python 3.9+
- AWS account with S3 access
- Quartr API key
- Google Gemini API key
- Perplexity API key
- Anthropic Claude API key
- Supabase account with table for company universe

## Setup

1. Clone the repository
2. Install dependencies
```
pip install -r requirements.txt
```

3. Configure Streamlit secrets
   Create a `.streamlit/secrets.toml` file locally for development or use the Streamlit Cloud secrets management. The secrets should include:
   ```
   AWS_ACCESS_KEY_ID = "your-aws-access-key"
   AWS_SECRET_ACCESS_KEY = "your-aws-secret-key"
   AWS_DEFAULT_REGION = "your-aws-region"
   S3_BUCKET_NAME = "your-s3-bucket"
   QUARTR_API_KEY = "your-quartr-api-key"
   GEMINI_API_KEY = "your-gemini-api-key"
   PERPLEXITY_API_KEY = "your-perplexity-api-key"
   CLAUDE_API_KEY = "your-claude-api-key"

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
   - QuartrID: Company ID from Quartr (required for document fetching)

## Project Structure
```
financial-insights-chat/
├── app.py                 # Main Streamlit application
├── supabase_client.py     # Supabase integration for company data
├── utils.py               # Utility classes for API, S3, and document processing
├── utils_helper.py        # Helper functions to resolve circular imports
├── logging_config.py      # Logging configuration
├── logger.py              # Logger instance used across the application
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

1. User selects a company from the dropdown in the sidebar
2. App fetches the company's Quartr ID from Supabase
3. When the user asks a question:
   - Perplexity API call starts immediately to search the web with company-specific research context
   - In parallel, if not already fetched:
     - App retrieves financial documents from Quartr API using the company ID
     - Documents are processed and stored in S3
   - Documents are downloaded from S3 and analyzed by Gemini
   - Claude synthesizes information from both Gemini and Perplexity
   - The comprehensive response is displayed with source information
4. For follow-up questions:
   - Previous conversation context is passed to all three models
   - Models can reference earlier questions and answers
   - No need to re-fetch documents, improving response time
   - Same multi-LLM pipeline runs with the added context

## Data Sources

The application leverages multiple data sources:
- **Company Documents**: Financial reports, presentations, and call transcripts from Quartr
- **Web Information**: Current news, analyses, and market data from Perplexity web search
- **Company Database**: Structured company information from Supabase
- **Conversation History**: Previous exchanges for contextual follow-up questions

This multi-source approach ensures comprehensive and up-to-date information for financial analysis.
