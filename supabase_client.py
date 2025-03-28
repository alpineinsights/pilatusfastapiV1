"""
This module handles the integration with Supabase to fetch company data.
Uses Streamlit's native Supabase integration.
"""

import streamlit as st
from typing import Dict, List, Optional

# Initialize Supabase connection using Streamlit's native integration
@st.cache_resource
def init_connection():
    """
    Initialize and cache the Supabase connection using Streamlit's native integration
    """
    return st.connection("supabase", type="sql")

@st.cache_data(ttl=60*60)  # Cache for 1 hour
def get_all_companies() -> List[Dict]:
    """
    Fetches all companies from the Supabase 'universe' table.
    
    Returns:
        List[Dict]: A list of company data dictionaries
    """
    try:
        conn = init_connection()
        rows = conn.query("SELECT * FROM universe;")
        return rows.to_dict('records')
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
        conn = init_connection()
        rows = conn.query(f"SELECT \"Quartr Id\" FROM universe WHERE \"Name\" = '{company_name}';")
        if not rows.empty and "Quartr Id" in rows.columns:
            return rows.iloc[0]["Quartr Id"]
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
        conn = init_connection()
        rows = conn.query(f"SELECT \"ISIN\" FROM universe WHERE \"Name\" = '{company_name}';")
        if not rows.empty and "ISIN" in rows.columns:
            return rows.iloc[0]["ISIN"]
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
        conn = init_connection()
        rows = conn.query(f"SELECT * FROM universe WHERE \"Quartr Id\" = '{quartrid}';")
        if not rows.empty:
            return rows.iloc[0].to_dict()
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
        conn = init_connection()
        rows = conn.query(f"SELECT * FROM universe WHERE \"ISIN\" = '{isin}';")
        if not rows.empty:
            return rows.iloc[0].to_dict()
        return None
    except Exception as e:
        st.error(f"Error fetching company by ISIN {isin}: {str(e)}")
        return None 
