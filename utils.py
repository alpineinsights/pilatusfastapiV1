import aiohttp
import io
import json
import logging
import os
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Optional, List
import base64
import uuid
import requests
from functools import lru_cache
from supabase_client import get_company_names, get_quartrid_by_name, get_all_companies

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get environment variables
QUARTR_API_KEY = os.getenv("QUARTR_API_KEY", "")
if not QUARTR_API_KEY:
    logger.error("QUARTR_API_KEY not found in environment variables")

# Initialize Supabase client for storage
@lru_cache(maxsize=1)
def init_supabase_storage_client():
    """Initialize and cache the Supabase client for storage operations"""
    from supabase_client import init_client
    return init_client()

class SupabaseStorageHandler:
    """Handler for Supabase storage operations"""
    
    def __init__(self):
        self.client = init_supabase_storage_client()
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "alpinedatalake")
    
    def create_filename(self, company_name: str, event_date: str, event_title: str, 
                       doc_type: str, original_filename: str) -> str:
        """Create a standardized filename with company, date, and type"""
        # Sanitize inputs to be safe for filenames
        safe_company = company_name.lower().replace(' ', '_').replace('-', '_')
        safe_date = event_date.replace('-', '')
        safe_title = event_title.lower().replace(' ', '_')[:30]  # Truncate to avoid very long filenames
        
        # Get file extension from original filename
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.pdf'  # Default extension if none is found
        
        # Create path format: company/type/company_date_type.ext
        filename = f"{safe_company}/{doc_type}/{safe_company}_{safe_date}_{doc_type}{ext}"
        return filename
    
    async def upload_file(self, file_data: bytes, filename: str, content_type: str = 'application/pdf') -> bool:
        """Upload a file to Supabase storage"""
        if not self.client:
            logger.error("Supabase client not initialized")
            return False
            
        try:
            # Format options according to Supabase API expectations
            upload_options = {
                "contentType": content_type,
                "upsert": "true"  # As string, not boolean
            }
            
            logger.info(f"Uploading file to {self.bucket_name}/{filename}")
            
            # Upload file to Supabase storage
            self.client.storage.from_(self.bucket_name).upload(
                path=filename,
                file=file_data,
                file_options=upload_options
            )
            
            logger.info(f"Successfully uploaded {filename} to Supabase bucket {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Error uploading file to Supabase storage: {str(e)}")
            
            # Try direct HTTP method as fallback
            try:
                logger.info(f"Attempting direct HTTP upload for {filename}")
                
                # Get Supabase credentials from environment variables
                supabase_url = os.getenv("SUPABASE_URL", "https://maeistbokyjhewrrisvf.supabase.co")
                supabase_key = os.getenv("SUPABASE_ANON_KEY")
                
                if not supabase_key:
                    logger.error("Missing Supabase key for direct upload")
                    return False
                
                url = f"{supabase_url}/storage/v1/object/{self.bucket_name}/{filename}"
                headers = {
                    "Authorization": f"Bearer {supabase_key}",
                    "Content-Type": content_type
                }
                
                response = requests.post(url, headers=headers, data=file_data)
                
                if response.status_code in (200, 201):
                    logger.info(f"Direct HTTP upload successful for {filename}")
                    return True
                
                logger.error(f"Direct HTTP upload failed: {response.status_code}")
            except Exception as fallback_error:
                logger.error(f"Direct HTTP upload attempt failed: {str(fallback_error)}")
            
            return False
    
    def get_public_url(self, filename: str) -> str:
        """Get the public URL for a file in Supabase storage"""
        if not self.client:
            return ""
            
        try:
            # First attempt to use the client method
            url = self.client.storage.from_(self.bucket_name).get_public_url(filename)
            
            # Clean up the URL by removing any trailing question mark
            if url:
                # Remove trailing question mark if present
                if url.endswith('?'):
                    url = url[:-1]
                return url
                
            # If that fails, construct the URL manually
            supabase_url = os.getenv("SUPABASE_URL", "https://maeistbokyjhewrrisvf.supabase.co")
            manual_url = f"{supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
            return manual_url
        except Exception as e:
            logger.error(f"Error getting public URL: {str(e)}")
            
            # Last resort fallback
            supabase_url = os.getenv("SUPABASE_URL", "https://maeistbokyjhewrrisvf.supabase.co")
            fallback_url = f"{supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
            return fallback_url
    
    async def download_file(self, filename: str, local_path: str) -> bool:
        """Download a file from Supabase storage to a local path"""
        if not self.client:
            logger.error("Supabase client not initialized")
            return False
            
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        try:
            logger.info(f"Attempting to download {filename} using Supabase client")
            # Download the file from Supabase storage
            response = self.client.storage.from_(self.bucket_name).download(filename)
            
            # Write the file to disk
            with open(local_path, 'wb') as f:
                f.write(response)
            
            # Verify file was downloaded successfully
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                logger.info(f"Successfully downloaded {filename} to {local_path}")
                return True
            else:
                logger.warning(f"Downloaded file exists but is empty: {local_path}")
        except Exception as e:
            logger.error(f"Error downloading file using Supabase client: {str(e)}")
            
            # If client download fails, try direct HTTP method
            try:
                logger.info(f"Attempting direct HTTP download for {filename}")
                
                # Get the direct URL to the file
                supabase_url = os.getenv("SUPABASE_URL", "https://maeistbokyjhewrrisvf.supabase.co")
                
                # Construct public URL
                public_url = f"{supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
                
                # Remove trailing question mark if present
                if public_url.endswith('?'):
                    public_url = public_url[:-1]
                
                response = requests.get(public_url, stream=True)
                
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                        logger.info(f"Direct HTTP download successful for {filename}")
                        return True
                else:
                    logger.error(f"Direct HTTP download failed: HTTP {response.status_code}")
            except Exception as http_error:
                logger.error(f"Direct HTTP download failed: {str(http_error)}")
        
        return False

class QuartrAPI:
    def __init__(self):
        if not QUARTR_API_KEY:
            raise ValueError("Quartr API key not found in environment variables")
        self.api_key = QUARTR_API_KEY
        self.base_url = "https://api.quartr.com/public/v1"
        self.headers = {"X-Api-Key": self.api_key}

    async def get_company_events(self, company_id: str, session: aiohttp.ClientSession, event_type: str = "all") -> Dict:
        """Get company events from Quartr API using company ID (not ISIN)"""
        url = f"{self.base_url}/companies/{company_id}/earlier-events"
        
        # Add query parameters
        params = {}
        if event_type != "all":
            params["type"] = event_type
        
        # Set limit to 10 to get enough events to select from
        params["limit"] = 10
        params["page"] = 1
        
        try:
            logger.info(f"Requesting earlier events from Quartr API for company ID: {company_id}")
            
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully retrieved earlier events for company ID: {company_id}")
                    
                    events = data.get('data', [])
                    
                    # Return the events data only
                    return {
                        'events': events
                    }
                else:
                    response_text = await response.text()
                    logger.error(f"Error fetching earlier events for company ID {company_id}: Status {response.status}, Response: {response_text}")
                    return {}
        except Exception as e:
            logger.error(f"Exception while fetching earlier events for company ID {company_id}: {str(e)}")
            return {}

    async def _get_company_name_direct(self, company_id: str, session: aiohttp.ClientSession) -> str:
        """Direct method to get company name only"""
        try:
            url = f"{self.base_url}/companies/{company_id}"
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('displayName', f"Company-{company_id}")
                return f"Company-{company_id}"
        except Exception:
            return f"Company-{company_id}"
    
    async def get_company_info(self, company_id: str, session: aiohttp.ClientSession) -> Dict:
        """Get basic company information using company ID"""
        url = f"{self.base_url}/companies/{company_id}"
        try:
            logger.info(f"Requesting company info from Quartr API for company ID: {company_id}")
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully retrieved company info for company ID: {company_id}")
                    return data
                else:
                    response_text = await response.text()
                    logger.error(f"Error fetching company info for company ID {company_id}: Status {response.status}, Response: {response_text}")
                    return {}
        except Exception as e:
            logger.error(f"Exception while fetching company info for company ID {company_id}: {str(e)}")
            return {}
    
    async def get_document(self, doc_url: str, session: aiohttp.ClientSession):
        """Get document from URL"""
        try:
            async with session.get(doc_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to fetch document from {doc_url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error getting document from {doc_url}: {str(e)}")
            return None

class TranscriptProcessor:
    @staticmethod
    async def process_transcript(transcript_url: str, transcripts: Dict, session: aiohttp.ClientSession) -> str:
        """Process transcript JSON into clean text"""
        try:
            # First try to get the raw transcript URL from the transcripts object
            raw_transcript_url = None
            
            # Check for different transcript types in Quartr
            if 'transcriptUrl' in transcripts and transcripts['transcriptUrl']:
                raw_transcript_url = transcripts['transcriptUrl']
            elif 'finishedLiveTranscriptUrl' in transcripts.get('liveTranscripts', {}) and transcripts['liveTranscripts']['finishedLiveTranscriptUrl']:
                raw_transcript_url = transcripts['liveTranscripts']['finishedLiveTranscriptUrl']
            
            # If no raw transcript URL is found, try the app transcript URL
            if not raw_transcript_url and transcript_url and 'app.quartr.com' in transcript_url:
                # Convert app URL to API URL if possible
                document_id = transcript_url.split('/')[-2]
                if document_id.isdigit():
                    raw_transcript_url = f"https://api.quartr.com/public/v1/transcripts/document/{document_id}"
                    headers = {"X-Api-Key": QUARTR_API_KEY}
                    async with session.get(raw_transcript_url, headers=headers) as response:
                        if response.status == 200:
                            transcript_data = await response.json()
                            if transcript_data and 'transcript' in transcript_data:
                                text = transcript_data['transcript'].get('text', '')
                                if text:
                                    # Format the text with proper line breaks and cleanup
                                    formatted_text = TranscriptProcessor.format_transcript_text(text)
                                    logger.info(f"Successfully processed transcript from API, length: {len(formatted_text)}")
                                    return formatted_text
            
            # If we have a raw transcript URL, fetch and process it
            if raw_transcript_url:
                logger.info(f"Fetching transcript from: {raw_transcript_url}")
                
                try:
                    headers = {"X-Api-Key": QUARTR_API_KEY} if 'api.quartr.com' in raw_transcript_url else {}
                    async with session.get(raw_transcript_url, headers=headers) as response:
                        if response.status == 200:
                            # Try processing as JSON first
                            try:
                                transcript_data = await response.json()
                                # Handle different JSON formats
                                if 'transcript' in transcript_data:
                                    text = transcript_data['transcript'].get('text', '')
                                    if text:
                                        formatted_text = TranscriptProcessor.format_transcript_text(text)
                                        logger.info(f"Successfully processed JSON transcript, length: {len(formatted_text)}")
                                        return formatted_text
                                elif 'text' in transcript_data:
                                    formatted_text = TranscriptProcessor.format_transcript_text(transcript_data['text'])
                                    logger.info(f"Successfully processed simple JSON transcript, length: {len(formatted_text)}")
                                    return formatted_text
                            except json.JSONDecodeError:
                                # Not a JSON, try processing as text
                                text = await response.text()
                                if text:
                                    formatted_text = TranscriptProcessor.format_transcript_text(text)
                                    logger.info(f"Successfully processed text transcript, length: {len(formatted_text)}")
                                    return formatted_text
                        else:
                            logger.error(f"Failed to fetch transcript: {response.status}")
                except Exception as e:
                    logger.error(f"Error processing raw transcript: {str(e)}")
            
            logger.warning(f"No transcript found or could be processed for URL: {transcript_url}")
            return ''
        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            return ''
    
    @staticmethod
    def format_transcript_text(text: str) -> str:
        """Format transcript text for better readability"""
        # Replace JSON line feed representations with actual line feeds
        text = text.replace('\\n', '\n')
        
        # Clean up extra whitespace
        text = ' '.join(text.split())
        
        # Format into paragraphs - break at sentence boundaries for better readability
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        formatted_text = '.\n\n'.join(sentences) + '.'
        
        return formatted_text

    @staticmethod
    def create_pdf(company_name: str, event_title: str, event_date: str, transcript_text: str) -> bytes:
        """Create a PDF from transcript text"""
        if not transcript_text:
            logger.error("Cannot create PDF: Empty transcript text")
            return b''
            
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        styles = getSampleStyleSheet()
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=30,
            textColor=colors.HexColor('#1a472a'),
            alignment=1
        )
        
        text_style = ParagraphStyle(
            'CustomText',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceBefore=6,
            fontName='Helvetica'
        )

        story = []
        
        # Create header with proper XML escaping
        header_text = f"""
            <para alignment="center">
            <b>{company_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</b><br/>
            <br/>
            Event: {event_title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}<br/>
            Date: {event_date}
            </para>
        """
        story.append(Paragraph(header_text, header_style))
        story.append(Spacer(1, 30))

        # Process transcript text
        paragraphs = transcript_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                # Clean and escape the text for PDF
                clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                try:
                    story.append(Paragraph(clean_para, text_style))
                    story.append(Spacer(1, 6))
                except Exception as e:
                    logger.error(f"Error adding paragraph to PDF: {str(e)}")
                    continue

        try:
            doc.build(story)
            pdf_data = buffer.getvalue()
            logger.info(f"Successfully created PDF, size: {len(pdf_data)} bytes")
            return pdf_data
        except Exception as e:
            logger.error(f"Error building PDF: {str(e)}")
            return b''
