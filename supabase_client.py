"""
This module handles the integration with Supabase to fetch company data.
Uses the Supabase Python client.
"""

import streamlit as st
from supabase import create_client
from typing import Dict, List, Optional
import os

# Initialize Supabase client
@st.cache_resource
def init_client():
    """
    Initialize and cache the Supabase client connection
    """
    try:
        # Get Supabase credentials from secrets
        supabase_url = st.secrets["supabase_url"]
        supabase_key = st.secrets["supabase_anon_key"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Error initializing Supabase client: {str(e)}")
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
            st.error("Failed to initialize Supabase client.")
            return []
            
        response = client.table('universe').select('*').execute()
        if hasattr(response, 'data'):
            return response.data
        return []
    except Exception as e:
        st.error(f"Error fetching companies from Supabase: {str(e)}")
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
            st.error("Failed to initialize Supabase client.")
            return None
            
        response = client.table('universe').select('\"Quartr Id\"').eq('Name', company_name).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("Quartr Id")
        return None
    except Exception as e:
        st.error(f"Error fetching Quartr ID for {company_name}: {str(e)}")
        return None

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_isin_by_name(company_name: str) -> Optional[str]:
    """
    Retrieves the ISIN code for a given company name from Supabase.
    
    Args:
        company_name (str): The company name to look up
        
    Returns:
        str: The ISIN code if found, None otherwise
    """
    try:
        client = init_client()
        if not client:
            st.error("Failed to initialize Supabase client.")
            return None
            
        response = client.table('universe').select('ISIN').eq('Name', company_name).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("ISIN")
        return None
    except Exception as e:
        st.error(f"Error fetching ISIN for {company_name}: {str(e)}")
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
            st.error("Failed to initialize Supabase client.")
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
