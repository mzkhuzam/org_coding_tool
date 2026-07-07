# =============================================================================
# ORGANIZATIONAL COMMENTS CODING APP
# =============================================================================

import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2 import service_account
from datetime import datetime
import time

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Organizational Comments Coding",
    page_icon="🏢",
    layout="wide"
)

st.title("OMB Organizational Comments Coding")
st.markdown("Identify whether comments are made **on behalf of an organization** vs. individuals.")

# Initialize session state for storing coded data
if 'coded_data' not in st.session_state:
    st.session_state.coded_data = []

# =============================================================================
# LABELLER IDENTITY
# =============================================================================
labeller = st.text_input("Enter your name:", key="labeller")

if not labeller:
    st.warning("Please enter your name ID above to begin coding.")
    st.stop()

# =============================================================================
# MAPPING DICTIONARIES
# =============================================================================
ORG_BINARY_MAPPING = {
    "Yes - Organizational": 1,
    "No - Individual": 0
}

WEB_BINARY_MAPPING = {
    "Yes - Website is correct": 1,
    "No - Website needs updating": 0
}

ORG_TYPE_MAPPING = {
    "Business/Corporation": "Business/Corporation",
    "Non-profit/NGO": "Non-profit/NGO",
    "Government Agency": "Government Agency",
    "Educational Institution": "Educational Institution",
    "Trade Association": "Trade Association",
    "Other": "Other",
    "Not Applicable (Individual)": "N/A"
}

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_data
def load_data():
    try:
        GOOGLE_CREDENTIALS = st.secrets["GOOGLE_CREDENTIALS"]
        GOOGLE_SHEET_URL = st.secrets["GOOGLE_SHEET_URL"]
        INPUT_SHEET_NAME = st.secrets["INPUT_SHEET_NAME"]
        
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
        gc = gspread.service_account_from_dict(creds_dict)
        
        sheet = gc.open_by_url(GOOGLE_SHEET_URL)
        input_worksheet = sheet.worksheet(INPUT_SHEET_NAME)
        data = input_worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df, sheet
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {str(e)}")
        st.stop()

df, sheet = load_data()
INPUT_SHEET_NAME = st.secrets["INPUT_SHEET_NAME"]

if df.empty:
    st.error("No data found in the spreadsheet!")
    st.stop()

# =============================================================================
# CODER ASSIGNMENTS
# =============================================================================
CODER_RANGES = {
    "Maya": {"start": 0, "end": 10, "name": "Maya"},
    "Sarah": {"start": 11, "end": 30, "name": "Sarah"}
}

if labeller in CODER_RANGES:
    range_info = CODER_RANGES[labeller]
    start = range_info["start"]
    end = min(range_info["end"], len(df))
    df_subset = df.iloc[start:end].reset_index(drop=True)
    if df_subset.empty:
        st.warning(f"⚠️ No records found in your assigned range.")
        st.stop()
    st.info(f"📋 {range_info['name']}, you have {len(df_subset)} records to code")
    df = df_subset
else:
    st.error(f"⚠️ Coder ID '{labeller}' not found.")
    st.stop()

# =============================================================================
# TRACK PROGRESS
# =============================================================================
def get_last_coded_index(labeller):
    return st.session_state.get(f"last_index_{labeller}", -1)

def save_progress(labeller, index):
    st.session_state[f"last_index_{labeller}"] = index

if 'index' not in st.session_state or st.session_state.get('current_labeller') != labeller:
    last_index = get_last_coded_index(labeller)
    st.session_state.index = last_index + 1
    st.session_state.current_labeller = labeller

# =============================================================================
# DISPLAY CURRENT RECORD
# =============================================================================
total_records = len(df)
current_index = st.session_state.index

if current_index < total_records:
    record = df.iloc[current_index]
    
    st.info(f"📊 Record {current_index + 1} of {total_records}")
    st.progress((current_index + 1) / total_records)
    
    st.markdown("### 📝 Comment to Code")
    comment_text = record.get('comment', '')
    if comment_text:
        st.markdown(f"**Comment:** {comment_text}")
    else:
        st.warning("⚠️ No comment text found.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Organization:** {record.get('organization', 'N/A')}")
        st.write(f"**First Name:** {record.get('firstName', 'N/A')}")
        st.write(f"**Last Name:** {record.get('lastName', 'N/A')}")
    with col2:
        website = record.get('website', '')
        st.write(f"**Website:** {website if website else 'Not provided'}")
        attachment = record.get('attachment_text', '')
        if attachment:
            preview = attachment[:200] + "..." if len(attachment) > 200 else attachment
            st.write(f"**Attachment:** {preview}")
        else:
            st.write("**Attachment:** None")
    with col3:
        existing_note = record.get('organization_detection_notes', '')
        st.write(f"**Existing note:** {existing_note if existing_note else 'None'}")
        existing_org_type = record.get('org_type', '')
        st.write(f"**Org type:** {existing_org_type if existing_org_type else 'Not filled'}")
    
    st.markdown("---")
    
    with st.expander("📖 Coding Guidelines", expanded=False):
        st.markdown("""
        **Organizational comments** = statements formally prepared and submitted **on behalf of an organization itself**.
        
        **Examples:**
        
        **What to look for:**
        1. "On behalf of [Organization]"
        2. Official titles (Director, President, CEO)
        3. Organizational letterhead
        4. Collective language ("we", "our organization")
        """)
    
    st.markdown("### 🏷️ Your Coding Decisions")
    
    is_organizational = st.radio(
        "**1. Is this an organizational comment?**",
        list(ORG_BINARY_MAPPING.keys()),
        key=f"is_org_{current_index}",
        horizontal=True,
        index=None
    )

    website_correct = st.radio(
        "**2. Is this the website correct?**",
        list(WEB_BINARY_MAPPING.keys()),
        key=f"website_correct_{current_index}",
        horizontal=True,
        index=None
    )
    
    notes = st.text_area(
        "**3. Coding Notes / Reasoning**",
        placeholder="Explain your reasoning...",
        key=f"notes_{current_index}",
        height=80
    )
    
    org_type = st.selectbox(
        "**3. Organization Type** (if organizational)",
        list(ORG_TYPE_MAPPING.keys()),
        key=f"org_type_{current_index}",
        index=None,
        placeholder="Choose an option..."
    )
    
    if is_organizational == "No - Individual":
        st.info("'Not Applicable' will be recorded for organization type.")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submit_button = st.button("✅ Submit", type="primary", use_container_width=True)
    
    if submit_button:
        validation_errors = []
        if not is_organizational:
            validation_errors.append("Please select whether this is organizational or not.")
        if is_organizational == "Yes - Organizational" and not org_type:
            validation_errors.append("Please select an organization type.")
        
        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            final_org_type = org_type if is_organizational == "Yes - Organizational" else "Not Applicable (Individual)"
            
            row = {
                "timestamp": datetime.now().isoformat(),
                "labeller": labeller,
                "record_index": current_index,
                "original_id": record.get('id', ''),
                "comment_text": comment_text,
                "is_organizational": ORG_BINARY_MAPPING[is_organizational],
                "is_organizational_text": is_organizational,
                "organization_detection_notes": notes,
                "org_type": ORG_TYPE_MAPPING.get(final_org_type, final_org_type),
                "original_org_field": record.get('organization', ''),
                "original_website": record.get('website', ''),
            }
            
            st.session_state.coded_data.append(row)
            st.success(f"✅ Record {current_index + 1} coded! ({len(st.session_state.coded_data)} total)")
            
            save_progress(labeller, current_index)
            time.sleep(0.5)
            st.session_state.index += 1
            st.rerun()
    
    # =========================================================================
    # DOWNLOAD BUTTON
    # =========================================================================
    if st.session_state.coded_data:
        st.markdown("---")
        st.markdown("### 💾 Download Your Coded Data")
        
        df_coded = pd.DataFrame(st.session_state.coded_data)
        csv = df_coded.to_csv(index=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"coded_data_{labeller}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col2:
            st.info(f"📊 Coded: {len(st.session_state.coded_data)} records")

else:
    st.balloons()
    st.markdown("## 🎉 You've coded all your assigned records!")
    st.markdown("Thank you for your work!")
    
    # Show download button when done
    if st.session_state.coded_data:
        st.markdown("### 💾 Download Your Coded Data")
        df_coded = pd.DataFrame(st.session_state.coded_data)
        csv = df_coded.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"coded_data_{labeller}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )