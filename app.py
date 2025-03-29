import streamlit as st
import pandas as pd
import os
import boto3
import tempfile
import uuid
import google.generativeai as genai
import time
from utils import QuartrAPI, S3Handler, TranscriptProcessor
import aiohttp
import asyncio
from typing import List, Dict, Tuple
import json
from supabase_client import get_company_names, get_isin_by_name, get_quartrid_by_name, get_all_companies

# Set page configuration
st.set_page_config(
    page_title="Financial Insights Chat",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "file_uploads" not in st.session_state:
    st.session_state.file_uploads = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []
if "current_company" not in st.session_state:
    st.session_state.current_company = None
if "company_data" not in st.session_state:
    st.session_state.company_data = None
if "documents_fetched" not in st.session_state:
    st.session_state.documents_fetched = False

# Load credentials from Streamlit secrets
try:
    # Access AWS credentials from aws section
    AWS_ACCESS_KEY_ID = st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
    AWS_DEFAULT_REGION = st.secrets["aws"]["AWS_DEFAULT_REGION"]
    S3_BUCKET_NAME = st.secrets["aws"]["S3_BUCKET_NAME"]
    
    # Access API keys from api_keys section
    GEMINI_API_KEY = st.secrets["api_keys"]["GEMINI_API_KEY"]
    QUARTR_API_KEY = st.secrets["api_keys"]["QUARTR_API_KEY"]
except KeyError as e:
    st.error(f"Missing required secret: {str(e)}. Please configure your secrets in Streamlit Cloud.")
    # Provide default values for development
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-central-2")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "alpineinsights")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    QUARTR_API_KEY = os.environ.get("QUARTR_API_KEY", "")

# Load company data from Supabase
@st.cache_data(ttl=60*60)  # Cache for 1 hour
def load_company_data():
    """Load company data from Supabase"""
    companies = get_all_companies()
    if not companies:
        st.error("Failed to load company data from Supabase.")
        return None
    return pd.DataFrame(companies)

# Initialize Gemini model
def initialize_gemini():
    if not GEMINI_API_KEY:
        st.error("Gemini API key not found in Streamlit secrets")
        return None
    
    try:
        # Configure the Gemini API with your API key
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    except Exception as e:
        st.error(f"Error initializing Gemini: {str(e)}")
        return None

# Function to process company documents
async def process_company_documents(company_id: str, event_type: str = "all") -> List[Dict]:
    """Process company documents and return list of file information"""
    try:
        async with aiohttp.ClientSession() as session:
            # Initialize API and handlers
            quartr_api = QuartrAPI()
            s3_handler = S3Handler()
            transcript_processor = TranscriptProcessor()
            
            # Get company data from Quartr API using company ID
            company_data = await quartr_api.get_company_events(company_id, session, event_type)
            if not company_data:
                return []
            
            company_name = company_data.get('displayName', 'Unknown Company')
            events = company_data.get('events', [])
            
            # Sort events by date (descending) and take the most recent events first
            events.sort(key=lambda x: x.get('eventDate', ''), reverse=True)
            
            processed_files = []
            transcript_count = 0
            report_count = 0
            slides_count = 0
            
            # Only process up to 6 documents in total (2 of each type)
            for event in events:
                # Stop processing if we have enough documents (2 of each type)
                if transcript_count >= 2 and report_count >= 2 and slides_count >= 2:
                    break
                    
                event_date = event.get('eventDate', '').split('T')[0]
                event_title = event.get('eventTitle', 'Unknown Event')
                
                # Only process the document types we need
                if transcript_count < 2 and event.get('transcriptUrl'):
                    # Process transcript
                    try:
                        transcripts = event.get('transcripts', {})
                        if not transcripts:
                            # If the transcripts object is empty, check for liveTranscripts
                            transcripts = event.get('liveTranscripts', {})
                        
                        transcript_text = await transcript_processor.process_transcript(
                            event.get('transcriptUrl'), transcripts, session
                        )
                        
                        if transcript_text:
                            pdf_data = transcript_processor.create_pdf(
                                company_name, event_title, event_date, transcript_text
                            )
                            
                            filename = s3_handler.create_filename(
                                company_name, event_date, event_title, 'transcript', 'transcript.pdf'
                            )
                            
                            success = await s3_handler.upload_file(
                                pdf_data, filename, S3_BUCKET_NAME, 'application/pdf'
                            )
                            
                            if success:
                                processed_files.append({
                                    'filename': filename,
                                    'type': 'transcript',
                                    'event_date': event_date,
                                    'event_title': event_title,
                                    's3_url': f"s3://{S3_BUCKET_NAME}/{filename}"
                                })
                                transcript_count += 1
                    except Exception as e:
                        st.error(f"Error processing transcript for {event_title}: {str(e)}")
                
                # Process report (if we need more)
                if report_count < 2 and event.get('reportUrl'):
                    try:
                        async with session.get(event.get('reportUrl')) as response:
                            if response.status == 200:
                                content = await response.read()
                                original_filename = event.get('reportUrl').split('/')[-1]
                                
                                filename = s3_handler.create_filename(
                                    company_name, event_date, event_title, 'report', original_filename
                                )
                                
                                success = await s3_handler.upload_file(
                                    content, filename, S3_BUCKET_NAME, 
                                    response.headers.get('content-type', 'application/pdf')
                                )
                                
                                if success:
                                    processed_files.append({
                                        'filename': filename,
                                        'type': 'report',
                                        'event_date': event_date,
                                        'event_title': event_title,
                                        's3_url': f"s3://{S3_BUCKET_NAME}/{filename}"
                                    })
                                    report_count += 1
                    except Exception as e:
                        st.error(f"Error processing report for {event_title}: {str(e)}")
                
                # Process slides/PDF (if we need more)
                if slides_count < 2 and event.get('pdfUrl'):
                    try:
                        async with session.get(event.get('pdfUrl')) as response:
                            if response.status == 200:
                                content = await response.read()
                                original_filename = event.get('pdfUrl').split('/')[-1]
                                
                                filename = s3_handler.create_filename(
                                    company_name, event_date, event_title, 'slides', original_filename
                                )
                                
                                success = await s3_handler.upload_file(
                                    content, filename, S3_BUCKET_NAME, 
                                    response.headers.get('content-type', 'application/pdf')
                                )
                                
                                if success:
                                    processed_files.append({
                                        'filename': filename,
                                        'type': 'slides',
                                        'event_date': event_date,
                                        'event_title': event_title,
                                        's3_url': f"s3://{S3_BUCKET_NAME}/{filename}"
                                    })
                                    slides_count += 1
                    except Exception as e:
                        st.error(f"Error processing slides for {event_title}: {str(e)}")
            
            return processed_files
    except Exception as e:
        st.error(f"Error processing company documents: {str(e)}")
        return []

# Function to download files from S3 to temporary location
def download_files_from_s3(file_infos: List[Dict]) -> List[str]:
    """Download files from S3 to temporary location and return local paths"""
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION
    )
    
    temp_dir = tempfile.mkdtemp()
    local_files = []
    
    for file_info in file_infos:
        try:
            s3_path = file_info['s3_url'].replace('s3://', '')
            bucket, key = s3_path.split('/', 1)
            
            local_path = os.path.join(temp_dir, file_info['filename'])
            s3_client.download_file(bucket, key, local_path)
            local_files.append(local_path)
        except Exception as e:
            st.error(f"Error downloading file from S3: {str(e)}")
    
    return local_files

# Function to query Gemini with file context
def query_gemini(query: str, file_paths: List[str]) -> str:
    """Query Gemini model with context from files"""
    try:
        # Make sure Gemini is initialized
        if not initialize_gemini():
            return "Error initializing Gemini client"
        
        # Create a model instance with proper configuration
        model = genai.GenerativeModel(
            'gemini-2.0-flash',
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=7000
            )
        )
        
        # Prepare files and content parts
        contents = []
        
        # Add files to contents
        for file_path in file_paths:
            try:
                # Open the file and create a content part
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    
                # Add file data as content part
                file_mime_type = 'application/pdf'  # Assuming all files are PDFs
                contents.append({
                    'mime_type': file_mime_type,
                    'data': file_data
                })
            except Exception as e:
                st.error(f"Error processing file for Gemini: {str(e)}")
        
        if not contents:
            return "No files were successfully processed for Gemini"
        
        # Add the prompt as the final content
        prompt = f"You are a senior financial analyst. Review the attached documents and provide a detailed and structured answer to the user's query. User's query: '{query}'"
        contents.append(prompt)
        
        # Generate content with files as context
        response = model.generate_content(contents)
        
        # Return the response text
        return response.text
    except Exception as e:
        st.error(f"Error querying Gemini: {str(e)}")
        return f"An error occurred while processing your query: {str(e)}"

# Main UI components
def main():
    st.title("Financial Insights Chat")
    
    # Load company data
    company_data = load_company_data()
    if company_data is None:
        st.error("Failed to load company data. Please check the Supabase connection.")
        return
    
    # Sidebar with company selection
    with st.sidebar:
        st.header("Select Company")
        company_names = get_company_names()
        selected_company = st.selectbox(
            "Choose a company:",
            options=company_names,
            index=0 if company_names else None
        )
        
        if selected_company:
            isin = get_isin_by_name(selected_company)
            quartr_id = get_quartrid_by_name(selected_company)
            
            # Check if company changed
            if st.session_state.current_company != selected_company:
                st.session_state.current_company = selected_company
                st.session_state.company_data = {
                    'name': selected_company,
                    'isin': isin,
                    'quartr_id': quartr_id
                }
                
                # Clear previous conversation when company changes
                st.session_state.chat_history = []
                st.session_state.processed_files = []
                st.session_state.documents_fetched = False
    
    # Main chat area
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if query := st.chat_input("Ask about the company..."):
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        
        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            response_placeholder.markdown("Thinking...")
            
            # Check if we have a selected company
            if not st.session_state.company_data:
                response = "Please select a company from the sidebar first."
                response_placeholder.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})
                return
            
            # Fetch documents if not already fetched
            if not st.session_state.documents_fetched:
                with st.spinner(f"Fetching documents for {st.session_state.company_data['name']}..."):
                    quartr_id = st.session_state.company_data['quartr_id']
                    processed_files = asyncio.run(process_company_documents(quartr_id))
                    st.session_state.processed_files = processed_files
                    st.session_state.documents_fetched = True
                    
                    if not processed_files:
                        response = "No documents found for this company. Please try another company or check your Quartr API key."
                        response_placeholder.markdown(response)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        return
            
            # Process the user query with the fetched documents
            if st.session_state.processed_files:
                with st.spinner("Processing your query with Gemini..."):
                    # Download files from S3
                    local_files = download_files_from_s3(st.session_state.processed_files)
                    
                    if not local_files:
                        response = "Error downloading files from S3. Please check your AWS credentials."
                        response_placeholder.markdown(response)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                        return
                    
                    # Query Gemini with file context
                    response = query_gemini(query, local_files)
                    
                    # Add sources section using S3 URLs from session state
                    response += "\n\n### Sources\n"
                    for i, file_info in enumerate(st.session_state.processed_files, 1):
                        # Parse the s3:// URL to get bucket and key
                        s3_url = file_info['s3_url']
                        
                        # Extract bucket and key from s3:// URL
                        if s3_url.startswith('s3://'):
                            # Remove the 's3://' prefix
                            s3_path = s3_url[5:]
                            # Split into bucket and key
                            parts = s3_path.split('/', 1)
                            if len(parts) == 2:
                                bucket, key = parts
                                # Create the https URL
                                https_url = f"https://{bucket}.s3.{AWS_DEFAULT_REGION}.amazonaws.com/{key}"
                                
                                # Use the key as the filename (last part of the path)
                                filename = os.path.basename(key)
                                
                                response += f"{i}. [{filename}]({https_url})\n"
                            else:
                                # Fallback if URL can't be parsed
                                response += f"{i}. [Document {i}]({s3_url})\n"
                        else:
                            # If not an s3:// URL, use as is
                            filename = os.path.basename(s3_url)
                            response += f"{i}. [{filename}]({s3_url})\n"
                    
                    # Display response with sources
                    response_placeholder.markdown(response)
                    
                    # Add assistant response to chat history
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
            else:
                response = "No documents are available for this company. Please try another company."
                response_placeholder.markdown(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()
