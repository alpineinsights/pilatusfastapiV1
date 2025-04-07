"""
This module handles the integration with Supabase to fetch company data.
Uses the Supabase Python client for more reliable connections.
"""

import streamlit as st
from supabase import create_client
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Initialize Supabase client
@st.cache_resource
def init_client():
    """
    Initialize and cache the Supabase client connection
    """
    try:
        # Show available secret keys for debugging
        # st.write("Available secret keys at root level:", list(st.secrets.keys()))
        
        # First try to get the service role key for higher privileges
        supabase_service_key = None
        if "supabase_service_role_key" in st.secrets:
            supabase_service_key = st.secrets["supabase_service_role_key"]
            logger.info("Found service role key for Supabase")
        
        # Try different paths to access Supabase settings
        if "supabase_url" in st.secrets and "supabase_anon_key" in st.secrets:
            supabase_url = st.secrets["supabase_url"]
            # Use service role key for admin operations if available, otherwise use anon key
            supabase_key = supabase_service_key or st.secrets["supabase_anon_key"]
            return create_client(supabase_url, supabase_key)
        elif "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            # If connection details exist, create the URL and try to find the key
            conn_info = st.secrets["connections"]["supabase"]
            if "host" in conn_info:
                host = conn_info["host"].replace("db.", "")
                supabase_url = f"https://{host}"
                
                # Look for the keys in order of preference
                if supabase_service_key:
                    return create_client(supabase_url, supabase_service_key)
                elif "supabase_anon_key" in st.secrets:
                    supabase_key = st.secrets["supabase_anon_key"]
                    return create_client(supabase_url, supabase_key)
                else:
                    st.error("Found Supabase host but missing API key")
        
        # Hard-code values as a last resort
        supabase_url = "https://maeistbokyjhewrrisvf.supabase.co"
        # For storage operations, we need a service role key with higher privileges
        # This is a fallback and should be replaced with proper secrets
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hZWlzdGJva3lqaGV3cnJpc3ZmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MTE2MzQxMzYsImV4cCI6MjAyNzIxMDEzNn0.pA5zcX2y7FHxcCg6-3yxK78KYtPK6W5B7NqocYh_tRY"
        st.warning("Using hardcoded connection details as fallback - storage operations may be limited due to permission constraints")
        return create_client(supabase_url, supabase_key)
        
    except Exception as e:
        st.error(f"Failed to initialize Supabase client: {str(e)}")
        return None

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_all_companies() -> List[Dict]:
    """
    Fetches all companies from the Supabase 'universe' table.
    
    Returns:
        List[Dict]: A list of company data dictionaries
    """
    try:
        client = init_client()
        if not client:
            return []
            
        response = client.table('universe').select('*').execute()
        if hasattr(response, 'data'):
            return response.data
        return []
    except Exception as e:
        st.error(f"Error fetching companies from Supabase: {str(e)}")
        # Fallback to direct SQL connection
        try:
            conn = st.connection("supabase", type="sql")
            rows = conn.query("SELECT * FROM universe;")
            return rows.to_dict('records')
        except Exception as e2:
            st.error(f"Fallback also failed: {str(e2)}")
            return []

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_company_names() -> List[str]:
    """
    Returns a list of all company names from Supabase.
    
    Returns:
        List[str]: A list of company names
    """
    companies = get_all_companies()
    return [company["Name"] for company in companies if "Name" in company]

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_quartrid_by_name(company_name: str) -> Optional[str]:
    """
    Retrieves the Quartr ID for a given company name from Supabase.
    
    Args:
        company_name (str): The company name to look up
        
    Returns:
        str: The Quartr ID if found, None otherwise
    """
    try:
        client = init_client()
        if not client:
            return None
            
        response = client.table('universe').select('\"Quartr Id\"').eq('Name', company_name).execute()
        if response.data and len(response.data) > 0:
            quartr_id = response.data[0].get("Quartr Id")
            logger.info(f"Found Quartr ID {quartr_id} for company: {company_name}")
            return str(quartr_id)  # Convert to string to ensure compatibility
        return None
    except Exception as e:
        st.error(f"Error fetching Quartr ID for {company_name}: {str(e)}")
        # Fallback to direct SQL if API fails
        try:
            conn = st.connection("supabase", type="sql")
            rows = conn.query(f"SELECT \"Quartr Id\" FROM universe WHERE \"Name\" = '{company_name}';")
            if not rows.empty and "Quartr Id" in rows.columns:
                quartr_id = rows.iloc[0]["Quartr Id"]
                logger.info(f"Found Quartr ID {quartr_id} for company: {company_name} (via SQL)")
                return str(quartr_id)  # Convert to string to ensure compatibility
        except:
            pass
        return None

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_isin_by_name(company_name: str) -> Optional[str]:
    """
    Retrieves the ISIN code for a given company name from Supabase.
    Note: This is kept for backward compatibility but is no longer the primary identifier.
    
    Args:
        company_name (str): The company name to look up
        
    Returns:
        str: The ISIN code if found, None otherwise
    """
    try:
        client = init_client()
        if not client:
            return None
            
        response = client.table('universe').select('ISIN').eq('Name', company_name).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("ISIN")
        return None
    except Exception as e:
        st.error(f"Error fetching ISIN for {company_name}: {str(e)}")
        # Fallback to direct SQL if API fails
        try:
            conn = st.connection("supabase", type="sql")
            rows = conn.query(f"SELECT \"ISIN\" FROM universe WHERE \"Name\" = '{company_name}';")
            if not rows.empty and "ISIN" in rows.columns:
                return rows.iloc[0]["ISIN"]
        except:
            pass
        return None

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_company_by_quartrid(quartrid: str) -> Optional[Dict]:
    """
    Retrieves company data for a given Quartr ID from Supabase.
    
    Args:
        quartrid (str): The Quartr ID to look up
        
    Returns:
        dict: The company data if found, None otherwise
    """
    try:
        client = init_client()
        if not client:
            return None
            
        response = client.table('universe').select('*').eq('\"Quartr Id\"', quartrid).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"Error fetching company by Quartr ID {quartrid}: {str(e)}")
        return None

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_company_by_isin(isin: str) -> Optional[Dict]:
    """
    Retrieves company data for a given ISIN code from Supabase.
    
    Args:
        isin (str): The ISIN code to look up
        
    Returns:
        dict: The company data if found, None otherwise
    """
    try:
        client = init_client()
        if not client:
            st.error("Failed to initialize Supabase client.")
            return None
            
        response = client.table('universe').select('*').eq('ISIN', isin).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"Error fetching company by ISIN {isin}: {str(e)}")
        return None
