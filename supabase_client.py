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
        # Use the provided explicit Supabase credentials
        supabase_url = "https://maeistbokyjhewrrisvf.supabase.co"
        supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1hZWlzdGJva3lqaGV3cnJpc3ZmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDMxNTgyMTUsImV4cCI6MjA1ODczNDIxNX0._Fb4I1BvmqMHbB5KyrtlEmPTyF8nRgR9LsmNFmiZSN8"
        
        # Debug - log available secret keys
        if hasattr(st, 'secrets'):
            logger.info(f"Available secret keys: {list(st.secrets.keys())}")
        
        # Try different potential key names
        if hasattr(st, 'secrets'):
            # Try different potential key names for URL
            potential_url_keys = ['supabase_url', 'SUPABASE_URL', 'NEXT_PUBLIC_SUPABASE_URL']
            for key in potential_url_keys:
                if key in st.secrets:
                    supabase_url = st.secrets[key]
                    logger.info(f"Found Supabase URL with key: {key}")
                    break
                    
            # Try different potential key names for anon key
            potential_anon_keys = ['supabase_anon_key', 'SUPABASE_ANON_KEY', 'NEXT_PUBLIC_SUPABASE_ANON_KEY']
            for key in potential_anon_keys:
                if key in st.secrets:
                    supabase_key = st.secrets[key]
                    logger.info(f"Found Supabase anon key with key: {key}")
                    break
                
        logger.info(f"Initializing Supabase client with URL: {supabase_url}")
        client = create_client(supabase_url, supabase_key)
        
        # Test client connection
        try:
            storage_buckets = client.storage.list_buckets()
            logger.info(f"Successfully connected to Supabase! Found {len(storage_buckets)} storage buckets.")
            # List the bucket names
            bucket_names = [bucket["name"] for bucket in storage_buckets]
            logger.info(f"Available buckets: {bucket_names}")
        except Exception as conn_error:
            logger.warning(f"Connected to Supabase but couldn't list buckets: {str(conn_error)}")
        
        logger.info("Supabase client initialized successfully")
        return client
        
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
