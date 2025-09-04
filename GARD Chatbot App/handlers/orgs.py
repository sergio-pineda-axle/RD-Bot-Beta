## Function:  Handle Patient Organization Queries

import streamlit as st
import re
import logging
import difflib
from utils.filtering import normalize_filters
from config.shared_data import org_disease_map, disease_synonym_map, DEBUG_MODE
from datetime import datetime


def handle_patient_org(filters, subject=None):
    
    # Step 1: Normalize the filter inputs and try to extract the disease name
    filters, disease = normalize_filters(filters, subject)
    if disease:
        disease = disease_synonym_map.get(disease.lower(), disease)
    matching_entries = []
    lines = []
    service_type_filter = None

    # DEBUG (Optional): Display the target and normalized disease name
    if DEBUG_MODE:
        logging.info(f"[ORG] Subject: {subject} | Normalized disease: {disease}")

    # Step 2a: If disease name is found, refer to services offered and retrieve service/url
    for org in org_disease_map:
        if disease and any(disease.lower() in d.lower() or d.lower() in disease.lower() for d in org.get("disease_name", [])):
            services = org.get("services_offered", [])
            filtered_services = [
                s for s in services
                if s.get("type") and s.get("url")
                and (not service_type_filter or service_type_filter in s["type"].lower())
            ]

            # If services are offered, provide formatted link to gpt for response
            if filtered_services:
                lines = [f"  - **{s['type'].title()}**: [Link]({s['url']})" for s in filtered_services]
                matching_entries.append(f"- **{org['org_name']}**\n" + "\n".join(lines))

    # Step 2b: If disease name is NOT found, fallback to match disease category to services
    if not matching_entries:
        for org in org_disease_map:
            if disease and any(disease.lower() == cat.lower() for cat in org.get("disease_category", [])):
                services = org.get("services_offered", [])
                filtered_services = [
                    s for s in services
                    if s.get("type") and s.get("url")
                    and (not service_type_filter or service_type_filter in s["type"].lower())
                ]

                # If services are offered, provide formatted link to gpt for response
                if filtered_services:
                    lines = [f"  - **{s['type'].title()}**: [Link]({s['url']})" for s in filtered_services]
                    diseases = org.get("disease_name", [])
                    disease_lines = [f"  - {d}" for d in sorted(diseases)] if diseases else ["  - No specific diseases listed."]
                    disease_block = "**Associated Diseases:**\n" + "\n".join(disease_lines)

                    matching_entries.append(
                        f"- **{org['org_name']}**\n{disease_block}\n\n" + "\n".join(lines)
                    )

                # If no services are offered to disease category, tell gpt
                if not lines:
                    lines.append("  - No specific services listed, but this organization supports this disease category.")


    # Step 2c: If no disease or category matched, try matching by org name
    if not matching_entries:
        for org in org_disease_map:
            org_name = org.get("org_name", "")
            org_name_lower = org_name.lower()
            disease_lower = disease.lower() if disease else ""

            if disease_lower in org_name_lower or org_name_lower in disease_lower:
                services = org.get("services_offered", [])
                diseases = org.get("disease_name", [])
                filtered_services = [
                    s for s in services
                    if s.get("type") and s.get("url")
                    and (not service_type_filter or service_type_filter in s["type"].lower())
                ]

                disease_lines = [f"  - {d}" for d in sorted(diseases)] if diseases else ["  - No specific diseases listed."]
                disease_block = "**Associated Diseases:**\n" + "\n".join(disease_lines)

                service_lines = [f"  - **{s['type'].title()}**: [Link]({s['url']})" for s in filtered_services]
                if not service_lines:
                    service_lines.append("  - No specific services listed, but this organization may be relevant.")

                matching_entries.append(
                    f"- **{org_name}**\n{disease_block}\n\n**Services Offered:**\n" + "\n".join(service_lines)
                )

    # Step 2d: If no disease name, category, or specific PO, log the entry 
    if not matching_entries:
        if DEBUG_MODE:
            st.warning(f"No match found for subject: {subject}")

        try:
            with open("logs/unmatched_patient_org_queries.log", "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"{datetime.now().isoformat()} — Unmatched subject: {subject or '[missing subject]'} → normalized: {disease or '[missing disease]'}\n"
                )
        except Exception as e:
            print(f"Logging failed: {e}")
        return f"No patient organizations found for **{disease}**."

    return f"## Patient Organizations for {disease}\n\n" + "\n\n".join(matching_entries)


# Function: Handle Organization Support Check Queries
def handle_org_support_check(subject, filters, org_disease_map):
    if isinstance(subject, list):
        names = [s for s in subject if isinstance(s, str)]
    else:
        names = [subject] if isinstance(subject, str) else []

    # ✅ NEW: If only an org name is provided, do reverse lookup
    if names and len(names) == 1:
        name = names[0].lower()
        for org in org_disease_map:
            org_name = org.get("org_name", "").lower()
            if name in org_name or name in org.get("org_url", "").lower():
                # New: Handle simple "what is the URL for X" case
                url = org.get("org_url")
                if url:
                    return f"The homepage for **{org['org_name']}** is: {url}"
                
                # Original fallback behavior
                diseases = org.get("disease_name", [])
                if diseases:
                    return f"🩺 **{org['org_name']}** supports:\n" + "\n".join(f"- {d}" for d in diseases)
                elif org.get("serves_people_with"):
                    return f"🩺 **{org['org_name']}** serves people with: {org['serves_people_with']}"
                else:
                    return f"⚠️ {org['org_name']} does not list specific diseases."

        return f"❌ No match found for organization: {name}"

    # ✅ FALLBACK: Run original check (org + disease both present)
    if len(names) < 2:
        return "❌ I need both at least one organization and one disease to check support."

    org_name, disease_name = names[0].lower(), names[1].lower()
    disease_name = disease_synonym_map.get(disease_name, disease_name)



    for org in org_disease_map:
        name = org.get("org_name", "").lower()
        diseases = [d.lower() for d in org.get("disease_name", [])]

        if org_name in name:
            if any(disease_name.lower() in d or d in disease_name.lower() for d in diseases):
                return f"✅ {org.get('org_name')} supports {disease_name.title()} as one of its listed conditions."
            else:
                return f"❌ {org.get('org_name')} does not list {disease_name.title()} as a supported condition."

    # Only reach this if no matching org was found
    return f"❌ No organization matching '{org_name.title()}' was found in the structured data."

# Function: Handle Organization Queries with 2 subjects (comparison)
def handle_organization_comparison(subject, filters, org_disease_map):

    if isinstance(subject, str) and (" and " in subject or " vs " in subject):
        parts = re.split(r"\band\b|\bvs\b", subject)
        subject = [p.strip() for p in parts if p.strip()]

    if not isinstance(subject, list) or len(subject) != 2:
        return "❌ I need two organizations to compare."

    if not all(subject) or not all(isinstance(s, str) for s in subject):
        return "❌ I need valid organization names to compare."

    name_a = subject[0].strip().lower() if subject[0] else ""
    name_b = subject[1].strip().lower() if subject[1] else ""
    org_a = org_b = None

    # Fuzzy match both orgs
    for org in org_disease_map:
        org_name = org.get("org_name", "").lower()
        if not org_a and (name_a in org_name or difflib.SequenceMatcher(None, name_a, org_name).ratio() > 0.85):
            org_a = org
        if not org_b and (name_b in org_name or difflib.SequenceMatcher(None, name_b, org_name).ratio() > 0.85):
            org_b = org

    if not org_a or not org_b:
        return "❌ Could not find both organizations."

    # Extract services
    services_a = {s["type"].lower() for s in org_a.get("services_offered", [])}
    services_b = {s["type"].lower() for s in org_b.get("services_offered", [])}

    common = services_a & services_b
    only_a = services_a - services_b
    only_b = services_b - services_a

    lines = [f"## Comparison of {org_a['org_name']} and {org_b['org_name']}"]

    if common:
        lines.append(f"**Shared Services:**")
        lines += [f"- {s.title()}" for s in sorted(common)]

    if only_a:
        lines.append(f"\n**Unique to {org_a['org_name']}:**")
        lines += [f"- {s.title()}" for s in sorted(only_a)]

    if only_b:
        lines.append(f"\n**Unique to {org_b['org_name']}:**")
        lines += [f"- {s.title()}" for s in sorted(only_b)]

    if not (common or only_a or only_b):
        lines.append("No service data available for either organization.")

    return "\n".join(lines)