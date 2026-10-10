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
import os
import re

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Organizational Comments Coding",
    page_icon="🏢",
    layout="wide"
)

st.title("OMB Organizational Comments Coding")


def safe_name(name: str) -> str:
    """Sanitize labeller name for use in filenames."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", name)


# =============================================================================
# PASSWORD
# =============================================================================
CORRECT_PASSWORD = os.environ.get("APP_PASSWORD")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔒 Password To Access")
    pwd = st.text_input("Enter password:", type="password", key="pwd_input")
    if st.button("Submit"):
        if pwd == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()

# =============================================================================
# MAPPING DICTIONARIES
# =============================================================================
ORG_BINARY_MAPPING = {
    "Yes - Organizational": 1,
    "No - Individual": 0,
    "Not sure - Flag": 99,
}

ORG_SECTOR_MAPPING = {
    "health": 1,
    "education": 2,
    "civil rights / racial and ethnic advocacy": 3,
    "legal": 4,
    "government / public administration": 5,
    "religious or cultural": 6,
    "business / economic": 7,
    "research": 8,
    "other": 99,
}

ORG_TYPE_MAPPING = {
    "nonprofit": 1,
    "association": 2,
    "corporation": 3,
    "small_business": 4,
    "union": 5,
    "state_local_gov": 6,
    "federal_gov": 7,
    "tribal_gov": 8,
    "university": 9,
    "informal_group": 10,
    "coalition": 11,
    "other": 99,
}

GEOGRAPHIC_SCOPE_MAPPING = {
    "national": 1,
    "state": 2,
    "local": 3,
    "tribal": 4,
    "international": 5,
    "other": 99,
}

INDIVIDUAL_TYPE_MAPPING = {
    "expert": 1,
    "citizen": 2,
    "unclear": 99,
}

ATTACHMENT_STATUS_MAPPING = {
    "missing or unreadable": 3,
}

CONFIDENCE_MAPPING = {
    1: 1,
    2: 2,
    3: 3,
}

# =============================================================================
# CODER ASSIGNMENTS
# =============================================================================
CODER_RANGES = {
    "Maya": {"start": 0, "end": 30, "name": "Maya"},
    "Leen": {"start": 0, "end": 30, "name": "Leen"},
}

# =============================================================================
# PREVIEW MODE FLAG
# =============================================================================
PREVIEW_MODE = os.environ.get("PREVIEW_MODE") == "1"

# =============================================================================
# LOAD DATA
# =============================================================================
@st.cache_resource
def connect_to_google_sheet():
    """Create and cache the Google Sheets connection."""
    google_credentials = os.environ["GOOGLE_CREDENTIALS"]
    google_sheet_url = os.environ["GOOGLE_SHEET_URL"]

    creds_dict = json.loads(google_credentials)
    gc = gspread.service_account_from_dict(creds_dict)

    return gc.open_by_url(google_sheet_url)


@st.cache_data(ttl=60)
def load_data():
    """Load worksheet data and cache it for 60 seconds."""
    sheet = connect_to_google_sheet()
    input_sheet_name = os.environ["INPUT_SHEET_NAME"]

    input_worksheet = sheet.worksheet(input_sheet_name)
    data = input_worksheet.get_all_records()

    return pd.DataFrame(data)


if PREVIEW_MODE:
    df = pd.DataFrame([
        {
            "id": "preview-1",
            "organization": "Preview Org A",
            "comment": "This is a fake comment for preview testing.",
            "attachment_text": "Fake attachment text.",
            "firstName": "Jane",
            "lastName": "Doe",
            "website": "https://example.org",
            "extra_notes": "",
        },
        {
            "id": "preview-2",
            "organization": "",
            "comment": "Second fake comment, no org.",
            "attachment_text": "",
            "firstName": "John",
            "lastName": "Smith",
            "website": "",
            "extra_notes": "Borderline case.",
        },
        {
            "id": "preview-3",
            "organization": "Preview Org C",
            "comment": "Third fake comment.",
            "attachment_text": "Some text.",
            "firstName": "",
            "lastName": "",
            "website": "https://example.com",
            "extra_notes": "",
        },
    ])
    st.warning("🧪 PREVIEW MODE — no data is being read from or written to Google Sheets.")
else:
    try:
        INPUT_SHEET_NAME = os.environ["INPUT_SHEET_NAME"]
        sheet = connect_to_google_sheet()
        df = load_data()

    except KeyError as e:
        st.error(f"Missing Render environment variable: {e.args[0]}")
        st.stop()

    except json.JSONDecodeError:
        st.error(
            "GOOGLE_CREDENTIALS is not valid JSON. In Render, its value must "
            "contain the complete service-account JSON object."
        )
        st.stop()

    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        st.stop()


if df.empty:
    st.error("No data found in the spreadsheet!")
    st.stop()

# =============================================================================
# LABELLER IDENTITY
# =============================================================================
labeller = st.text_input("Enter your name:", key="labeller")

if not labeller:
    st.warning("Please enter your name ID above to begin coding.")
    st.stop()

if labeller not in CODER_RANGES:
    st.error(f"⚠️ Coder ID '{labeller}' not found. Check with the research team.")
    st.stop()

# Initialize session state on first run
if "coded_data" not in st.session_state:
    st.session_state.coded_data = []
if "index" not in st.session_state:
    st.session_state.index = 0

# =============================================================================
# SAVE / LOAD CONTROLS (always visible)
# =============================================================================
st.markdown("### 💾 Save / Load Progress")

col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.session_state.coded_data:
        resume_payload = json.dumps({
            "labeller": labeller,
            "saved_at": datetime.now().isoformat(),
            "index": st.session_state.index,
            "coded_data": st.session_state.coded_data,
        }, indent=2, default=str)
        st.download_button(
            label="💾 Save progress to file",
            data=resume_payload,
            file_name=f"{safe_name(labeller)}_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
            help="Download this file to continue later or on another computer.",
        )
    else:
        st.button(
            "💾 Save progress to file",
            disabled=True,
            use_container_width=True,
            help="Nothing coded yet.",
        )

with col2:
    uploaded = st.file_uploader(
        "📤 Load progress from file",
        type=["json"],
        key="always_resume_upload",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        try:
            payload = json.load(uploaded)
            st.session_state.coded_data = payload.get("coded_data", [])
            st.session_state.index = payload.get("index", 0)
            st.success(
                f"✅ Restored {len(st.session_state.coded_data)} records. "
                f"Continuing at record {st.session_state.index + 1}."
            )
            time.sleep(0.8)
            st.rerun()
        except Exception as e:
            st.error(f"Could not read file: {e}")

with col3:
    if st.session_state.coded_data:
        st.info(f"📊 {len(st.session_state.coded_data)} coded")
    else:
        st.info("📊 0 coded")

st.markdown("---")

# =============================================================================
# SLICE DATAFRAME TO CODER'S ASSIGNED RANGE
# =============================================================================
range_info = CODER_RANGES[labeller]
start = range_info["start"]
end = min(range_info["end"], len(df))
df_subset = df.iloc[start:end].reset_index(drop=True)

if df_subset.empty:
    st.warning("⚠️ No records found in your assigned range.")
    st.stop()

st.info(f"📋 {range_info['name']}, you have {len(df_subset)} records to code")
df = df_subset

# =============================================================================
# DISPLAY CURRENT RECORD
# =============================================================================
total_records = len(df)
current_index = st.session_state.index

if current_index < total_records:
    record = df.iloc[current_index]

    st.info(f"📊 Record {current_index + 1} of {total_records}")
    st.progress((current_index + 1) / total_records)

    st.markdown("### Comment ID")
    st.write(f"{record.get('id', 'N/A')}")
    st.markdown("---")
    
    st.markdown("### Organization")
    st.write(f"{record.get('organization', 'N/A')}")
    st.markdown("---")

    st.markdown("### Comment")
    comment_text = record.get('comment', '')
    if comment_text:
        st.markdown(f"{comment_text}")
    else:
        st.warning("⚠️ No comment text found.")

    st.markdown("---")

    st.markdown("### Attachment Text")
    attachment = record.get('attachment_text', '')
    if attachment:
        with st.expander("### Click for full text", expanded=False):
            st.write(attachment)
    else:
        st.write("None")

    st.markdown("---")

    col1 = st.columns(1)[0]
    with col1:
         st.write(f"**First Name:** {record.get('firstName', 'N/A')}")
         st.write(f"**Last Name:** {record.get('lastName', 'N/A')}")

    st.markdown("---")

    st.markdown("### 🏷️ Your Coding Decisions")

    is_organizational = st.radio(
        "**1. Is this an organizational comment?**",
        list(ORG_BINARY_MAPPING.keys()),
        key=f"is_org_{current_index}",
        horizontal=True,
        index=None
    )

    website_choice = st.radio(
        "**2. Website**",
        ["Fill in", "None found"],
        key=f"website_choice_{current_index}",
        horizontal=True,
        index=None
    )

    website_entry = None
    if website_choice == "Fill in":
        website_entry = st.text_input(
            "**Website URL**",
            key=f"website_entry_{current_index}",
            placeholder="https://..."
        )

    individual_type = None
    if is_organizational == "No - Individual":
        individual_type = st.selectbox(
            "**3. Individual type**",
            list(INDIVIDUAL_TYPE_MAPPING.keys()),
            key=f"individual_type_{current_index}",
            index=None,
            placeholder="Choose an option..."
        )

    org_sector = org_sector_other = None
    org_type = org_type_other = None
    population_served = None
    geographic_scope = geographic_scope_other = None

    if is_organizational == "Yes - Organizational":
        org_sector = st.multiselect(
            "**3. Organization sector** (select all that apply)",
            list(ORG_SECTOR_MAPPING.keys()),
            key=f"org_sector_{current_index}",
            placeholder="Choose one or more..."
        )
        if "other" in (org_sector or []):
            org_sector_other = st.text_input(
                "**Specify organization sector**",
                key=f"org_sector_other_{current_index}",
                placeholder="Describe the sector..."
            )

        org_type = st.selectbox(
            "**4. Organization type**",
            list(ORG_TYPE_MAPPING.keys()),
            key=f"org_type_{current_index}",
            index=None,
            placeholder="Choose an option..."
        )
        if org_type == "other":
            org_type_other = st.text_input(
                "**Specify organization type**",
                key=f"org_type_other_{current_index}",
                placeholder="Describe the type..."
            )

        population_served = st.text_area(
            "**5. Population served** (optional)",
            key=f"population_served_{current_index}",
            height=80
        )

        geographic_scope = st.selectbox(
            "**6. Geographic scope**",
            list(GEOGRAPHIC_SCOPE_MAPPING.keys()),
            key=f"geographic_scope_{current_index}",
            index=None,
            placeholder="Choose an option..."
        )
        if geographic_scope == "other":
            geographic_scope_other = st.text_input(
                "**Specify geographic scope**",
                key=f"geographic_scope_other_{current_index}",
                placeholder="Describe the scope..."
            )

    confidence = st.radio(
        "**Confidence**",
        [1, 2, 3],
        key=f"confidence_{current_index}",
        horizontal=True,
        index=None,
        format_func=lambda x: {
            1: "1 = certain",
            2: "2 = fairly sure",
            3: "3 = unsure",
        }[x]
    )

    attachment_problem = st.checkbox(
        "⚠️ Attachment is missing or unreadable (check only if there's a problem)",
        key=f"attachment_problem_{current_index}"
    )
    
    attachment_status = "missing or unreadable" if attachment_problem else None

    notes = st.text_area(
        "**Extra notes:**",
        key=f"notes_{current_index}",
        height=80
    )

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submit_button = st.button("✅ Submit", type="primary", use_container_width=True)

    if submit_button:
        validation_errors = []
        if not is_organizational:
            validation_errors.append("Please select whether this is organizational or not.")
        if not website_choice:
            validation_errors.append("Please select a website option.")
        if website_choice == "Fill in" and not website_entry:
            validation_errors.append("Please enter the website URL.")
        if is_organizational == "No - Individual" and not individual_type:
            validation_errors.append("Please select an individual type.")
        if is_organizational == "Yes - Organizational":
            if not org_sector:
                validation_errors.append("Please select an organization sector.")
            if org_sector == "other" and not org_sector_other:
                validation_errors.append("Please specify the organization sector.")
            if not org_type:
                validation_errors.append("Please select an organization type.")
            if org_type == "other" and not org_type_other:
                validation_errors.append("Please specify the organization type.")
            if not geographic_scope:
                validation_errors.append("Please select a geographic scope.")
            if geographic_scope == "other" and not geographic_scope_other:
                validation_errors.append("Please specify the geographic scope.")
            # population_served is optional
        if confidence is None:
            validation_errors.append("Please select a confidence level.")

        if validation_errors:
            for error in validation_errors:
                st.error(error)
        else:
            row = {
                "timestamp": datetime.now().isoformat(),
                "labeller": labeller,
                "record_index": current_index,
                "original_id": record.get('id', ''),
                "comment_text": comment_text,

                "website": website_entry if website_choice == "Fill in" else "none found",
                "website_choice": website_choice,
                "extra_notes": notes,

                "is_organizational": ORG_BINARY_MAPPING.get(is_organizational),
                "is_organizational_text": is_organizational,

                "individual_type": INDIVIDUAL_TYPE_MAPPING.get(individual_type) if individual_type else None,
                "individual_type_text": individual_type,

                "org_sector": ORG_SECTOR_MAPPING.get(org_sector) if org_sector else None,
                "org_sector_text": org_sector,
                "org_sector_other": org_sector_other,

                "org_type": ORG_TYPE_MAPPING.get(org_type) if org_type else None,
                "org_type_text": org_type,
                "org_type_other": org_type_other,

                "population_served": population_served,

                "geographic_scope": GEOGRAPHIC_SCOPE_MAPPING.get(geographic_scope) if geographic_scope else None,
                "geographic_scope_text": geographic_scope,
                "geographic_scope_other": geographic_scope_other,

                "confidence": CONFIDENCE_MAPPING.get(confidence) if confidence else None,

                "attachment_status": ATTACHMENT_STATUS_MAPPING.get(attachment_status) if attachment_status else None,
                "attachment_status_text": attachment_status,

                "original_org_field": record.get('organization', ''),
                "original_website": record.get('website', ''),
            }

            st.session_state.coded_data.append(row)
            st.success(f"✅ Record {current_index + 1} coded! ({len(st.session_state.coded_data)} total)")

            time.sleep(0.5)
            st.session_state.index += 1
            st.rerun()


# =============================================================================
# DOWNLOAD ANALYSIS CSV
# =============================================================================
def render_download_section():
    if not st.session_state.coded_data:
        return

    st.markdown("---")
    st.markdown("### 📥 Download Analysis CSV")

    df_coded = pd.DataFrame(st.session_state.coded_data)

    preferred_cols = [
        "timestamp", "labeller", "record_index", "original_id", "comment_text",
        "website", "website_choice", "extra_notes",
        "is_organizational", "is_organizational_text",
        "individual_type", "individual_type_text",
        "org_sector", "org_sector_text", "org_sector_other",
        "org_type", "org_type_text", "org_type_other",
        "population_served",
        "geographic_scope", "geographic_scope_text", "geographic_scope_other",
        "confidence",
        "attachment_status", "attachment_status_text",
        "original_org_field", "original_website",
    ]
    ordered_cols = [c for c in preferred_cols if c in df_coded.columns]
    ordered_cols += [c for c in df_coded.columns if c not in ordered_cols]
    df_coded = df_coded[ordered_cols]

    csv = df_coded.to_csv(index=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    st.download_button(
        label="📥 Download analysis CSV",
        data=csv,
        file_name=f"coded_data_{safe_name(labeller)}_{ts}.csv",
        mime="text/csv",
        use_container_width=True,
        help="Send this file to the research team when you're done coding."
    )


if current_index < total_records:
    render_download_section()
else:
    st.markdown("## 🎉 You've coded all your assigned records!")
    st.markdown("Thank you for your work!")
    render_download_section()
