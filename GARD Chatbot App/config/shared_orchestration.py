from openai import AzureOpenAI
from config.shared_data import DEBUG_MODE, aoai_endpoint, aoai_subscription_key, aoai_api_version, gpt_deployment, org_name_lookup, disease_synonym_map
import logging
import json
import re
import streamlit as st

# config/shared_orchestration.py


def dispatch_tool(intent, entities, filters, query, maps):
    """
    Executes the appropriate handler based on the intent.
    Returns a structured dictionary:
        {
            "intent": <intent_name>,
            "display": <markdown-formatted block>,
            "summary": <optional summary>,
            "source": <"symptom_handler" | "org_handler" | "assistant">
        }
    """
    disease_symptom_map, org_disease_map = maps

    if not isinstance(entities, dict):
        if DEBUG_MODE:
            st.warning("⚠️ Entities malformed — using legacy fallback.")
        entities = {
            "disease": [],
            "organization": [],
            "symptom": [],
            "body_system": [],
            "service_type": []
        }

    # Normalize any acronyms in entities["organization"]
    if isinstance(entities, dict) and "organization" in entities:
        resolved_orgs = []
        for org in entities["organization"]:
            resolved = org_name_lookup.get(org.lower())
            if resolved:
                resolved_orgs.append(resolved.get("org_name", org))
            else:
                resolved_orgs.append(org)  # fallback to original
        entities["organization"] = resolved_orgs

        print("[DEBUG] Normalized organizations:", entities.get("organization"))

    # Normalize any acronyms or variants in entities["disease"]
    if isinstance(entities, dict) and "disease" in entities:
        from config.shared_data import disease_synonym_map
        def normalize_disease_name(name: str) -> str:
            # Lowercase
            name = name.lower()
            # Replacemultiple spaces with a single space
            name = re.sub(r"\s+", " ", name)
            # Strip leading/trailing spaces
            name = name.strip()
            return name

        resolved_diseases = []
        for dis in entities["disease"]:
            norm_dis = normalize_disease_name(dis)
            resolved = disease_synonym_map.get(norm_dis, dis)
            resolved_diseases.append(resolved)
        entities["disease"] = resolved_diseases

        print("[DEBUG] Normalized diseases:", entities.get("disease"))

    # Handle backward compatibility and multi-entity logic
    subject = None
    if intent in {"symptoms_list", "semantic", "symptom_comparison", "code_interpreter"}:
        if isinstance(entities, dict):
            subject = entities.get("disease", [])
        else:
            subject = entities  # fallback for old-style string

        if not isinstance(entities, dict):
            if DEBUG_MODE:
                st.warning("⚠️ Entities not structured — falling back to legacy subject.")

    elif intent in {"patient_org", "org_support_check", "organization_comparison"}:
        orgs = entities.get("organization", [])
        dis = [disease_synonym_map.get(d.lower(), d) for d in entities.get("disease", [])]
        if intent == "org_support_check":
            subject = orgs + dis
        elif intent == "patient_org":
            subject = orgs if orgs else dis
        else:
            subject = orgs

    # Collapse singleton lists into string
    if isinstance(subject, list) and len(subject) == 1:
        subject = subject[0]

    # Validate entities
    required_types = {
        "symptom_comparison": "disease",
        "organization_comparison": "organization",
        "org_support_check": ["organization", "disease"]
    }

    expected = required_types.get(intent)
    malformed = False

    if expected:
        if isinstance(expected, str):
            malformed = not entities.get(expected)
        elif isinstance(expected, list):
            malformed = not all(entities.get(e) for e in expected)

    if malformed:
        if DEBUG_MODE:
            st.warning(f"⚠️ Entity mismatch for intent '{intent}': {entities}")
        try:
            with open("logs/invalid_entity_dispatch.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "intent": intent,
                    "entities": entities,
                    "filters": filters,
                    "query": query
                }) + "\n")
        except Exception as e:
            print(f"[Logging failed] {e}")

    # Intents
    if intent == "symptoms_list":
        from handlers.symptom import handle_symptoms
        result = handle_symptoms(filters, subject)
        return {
            "intent": intent,
            "display": result,
            "summary": None,
            "source": "symptom_handler"
        } if result else None

    elif intent == "symptom_comparison":
        from handlers.symptom import handle_symptom_comparison
        disease_list = entities.get("disease", [])
        if len(disease_list) < 2:
            if DEBUG_MODE:
                st.warning("❌ I need two diseases to compare.")
            return None
        return {
            "intent": intent,
            "source": "symptom_handler",
            "display": handle_symptom_comparison(filters, disease_list, disease_symptom_map),
            "summary": f"Compared symptoms across diseases."
        }

    elif intent == "symptom_lookup_reverse":
        subject = []
        for sym in entities.get("symptom", []):
            if isinstance(sym, dict):
                val = sym.get("value")
            else:
                val = sym
            if isinstance(val, str):
                subject.append(val.strip())

        from handlers.symptom import handle_symptom_lookup_reverse
        return {
            "intent": intent,
            "source": "symptom_handler",
            "display": handle_symptom_lookup_reverse(filters, subject, disease_symptom_map),
            "summary": f"Listed diseases with the symptom(s): {', '.join(subject)}"
        }

    elif intent == "patient_org":
        from handlers.orgs import handle_patient_org
        result = handle_patient_org(filters, subject)
        return {
            "intent": intent,
            "display": result,
            "summary": None,
            "source": "org_handler"
        } if result else None
    
    elif intent == "org_support_check":
        from handlers.orgs import handle_org_support_check
        return {
            "intent": intent,
            "source": "org_handler",
            "display": handle_org_support_check(subject, filters, org_disease_map),
            "summary": f"Checked whether an organization supports a specific disease."
        }
    
    elif intent == "organization_comparison":
        from handlers.orgs import handle_organization_comparison
        org_list = entities.get("organization", [])
        if len(org_list) < 2:
            if DEBUG_MODE:
                st.warning("❌ I need two organizations to compare.")
            return None
        return {
            "intent": intent,
            "source": "org_handler",
            "display": handle_organization_comparison(org_list, filters, org_disease_map),
            "summary": f"Compared services between two organizations."
        }

    elif intent == "code_interpreter":
        from handlers.code_assistant import call_code_interpreter_assistant, preprocess_for_assistant
        from services.plan_data_extraction import plan_data_extraction

        client = AzureOpenAI(
            api_key=aoai_subscription_key,
            api_version=aoai_api_version,
            azure_endpoint=aoai_endpoint
        )

        # Determine subject type
        is_org = all(s.lower().strip() in org_disease_map for s in subject) if isinstance(subject, list) else subject.lower().strip() in org_disease_map
        subject_type = "organization" if is_org else "disease"

        # Field options GPT can select from
        available_fields = {
            "disease": ["symptom_name", "symptom_synonyms", "frequency", "frequency_rank", "body_systems"],
            "organization": ["org_name", "org_url", "disease_name", "disease_category", "serves_people_with", "services_offered", "country", "language"]
        }

        # GPT plans what fields to extract
        plan = plan_data_extraction(
            client=client,
            deployment=gpt_deployment,
            query=query,
            subject_type=subject_type,
            available_fields=available_fields
        )

        # Extract only the needed structured fields (no filtering)
        filter_dict = {f["field"]: f["value"] for f in filters}
        structured_data = preprocess_for_assistant(
            subject,
            filter_dict.get("body_system"),
            filter_dict.get("symptom_frequency"),
            plan=plan
        )

        if not structured_data:
            return {
                "intent": intent,
                "display": "⚠️ No structured data could be prepared for this query.",
                "summary": None,
                "source": "assistant"
            }

        result = call_code_interpreter_assistant(
            "code_interpreter", filters, subject, structured_data, query
        )

        if isinstance(result, dict):
            return {
                "intent": intent,
                "display": result.get("display", ""),
                "summary": result.get("summary", ""),
                "source": "assistant",
                "image_data": result.get("image_data")
            }

        return {
            "intent": intent,
            "display": result,
            "summary": None,
            "source": "assistant"
        } if result else None
    
    print("[DEBUG] No result returned — intent may not be implemented:", intent)


    return None
