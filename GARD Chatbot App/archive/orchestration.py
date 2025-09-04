# config/shared_orchestration.py

def dispatch_tool(intent, subject, filters, query, maps):
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

    if intent == "symptoms_list":
        from handlers.symptom import handle_symptoms
        result = handle_symptoms(filters, subject)
        return {
            "intent": intent,
            "display": result,
            "summary": None,
            "source": "symptom_handler"
        } if result else None

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

    elif intent == "code_interpreter":
        from handlers.code_assistant import call_code_interpreter_assistant
        result = call_code_interpreter_assistant(
            "code_interpreter", filters, subject, disease_symptom_map, org_disease_map, query
        )
        if isinstance(result, dict):
            return {
                "intent": intent,
                "display": result.get("display", ""),
                "summary": result.get("summary", ""),
                "source": "assistant"
            }
        return {
            "intent": intent,
            "display": result,
            "summary": None,
            "source": "assistant"
        } if result else None

    return None
