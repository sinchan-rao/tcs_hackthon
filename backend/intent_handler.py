from backend.banking_service import (
    get_balance, get_transactions, get_account_details,
    get_loan_information, calculate_emi, get_interest_rates,
    analyze_spending, transfer_money, get_faqs
)

# In-memory session store for conversational state & pending transfers
SESSION_STORE = {}

def get_session(session_id: str):
    if not session_id:
        session_id = "default_session"
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = {
            "history": [],
            "pending_transfer": None,
            "pending_action": None,
            "otp_verified": False
        }
    return SESSION_STORE[session_id]

def clear_pending_transfer(session_id: str):
    session = get_session(session_id)
    session["pending_transfer"] = None

def execute_personal_intent(intent: str, entities: dict, customer_id: str):
    """Executes authenticated personal data retrieval"""
    if intent == "balance_enquiry":
        bal = get_balance(customer_id)
        if bal is None:
            return {"error": "Customer account not found."}
        return {"intent": "balance_enquiry", "balance": bal, "customer_id": customer_id}

    elif intent == "transaction_history":
        txns = get_transactions(customer_id)
        return {"intent": "transaction_history", "transactions": txns[:5], "customer_id": customer_id}

    elif intent == "account_details":
        acc = get_account_details(customer_id)
        if not acc:
            return {"error": "Account details not found."}
        return {"intent": "account_details", "account": acc}

    elif intent == "spending_analysis":
        spending = analyze_spending(customer_id)
        spending["intent"] = "spending_analysis"
        spending["focus"] = entities.get("focus", "highest")
        return spending

    elif intent == "loan_information":
        loans = get_loan_information(customer_id)
        return {"intent": "loan_information", "loans": loans, "customer_id": customer_id}

    return {"error": "Unknown personal request."}

def handle_intent(intent: str, entities: dict, customer_id: str, is_auth: bool, session_id: str = "default_session", raw_text: str = ""):
    session = get_session(session_id)
    
    # 0. Check if user is responding to an OTP challenge
    pending_transfer = session.get("pending_transfer")
    pending_action = session.get("pending_action")
    clean_digits = "".join(filter(str.isdigit, raw_text))
    
    if (clean_digits == "123456" or "123456" in raw_text):
        if pending_transfer:
            # Execute transfer
            result = transfer_money(customer_id, pending_transfer["recipient"], pending_transfer["amount"])
            session["pending_transfer"] = None
            if result.get("success"):
                return {
                    "intent": "fund_transfer",
                    "action": "transfer_success",
                    "success": True,
                    "amount": pending_transfer["amount"],
                    "recipient": result.get("recipient", pending_transfer["recipient"]),
                    "remaining_balance": result.get("remaining_balance"),
                    "transaction_id": result.get("transaction_id"),
                    "message": result.get("message")
                }
            else:
                return {"error": result.get("error", "Transfer failed.")}
                
        elif pending_action:
            # Verify session for personal data access
            session["otp_verified"] = True
            act_intent = pending_action.get("intent", "balance_enquiry")
            act_entities = pending_action.get("entities", {})
            session["pending_action"] = None
            
            # Execute the pending personal intent
            data = execute_personal_intent(act_intent, act_entities, customer_id)
            data["otp_verified_now"] = True
            return data

    # 1. Auth check for personal data
    requires_auth = [
        "balance_enquiry", "transaction_history", "account_details",
        "spending_analysis", "fund_transfer"
    ]
    if intent in requires_auth and not is_auth:
        return {"error": "Please log in first to access your personal account information."}

    # 2. Check if personal financial queries require OTP verification
    # For personal money inquiries (balance, transactions, spending), ask for OTP on first access in session
    personal_money_intents = ["balance_enquiry", "transaction_history", "spending_analysis", "account_details"]
    if intent in personal_money_intents and not session.get("otp_verified"):
        demo_otp = "123456"
        session["pending_action"] = {
            "intent": intent,
            "entities": entities
        }
        return {
            "action_required": "otp_verification",
            "scope": "personal_data",
            "target_intent": intent,
            "demo_otp": demo_otp,
            "message": f"For your security, a verification OTP has been sent to your registered mobile (98XXXXXX21).\n\nDemo OTP: {demo_otp}\n\nPlease enter the OTP to access your personal account information."
        }

    # 3. Handle specific intents
    if intent == "greeting":
        return {"intent": "greeting"}

    if intent == "balance_enquiry":
        return execute_personal_intent("balance_enquiry", entities, customer_id)

    elif intent == "transaction_history":
        return execute_personal_intent("transaction_history", entities, customer_id)

    elif intent == "account_details":
        return execute_personal_intent("account_details", entities, customer_id)

    elif intent == "loan_information":
        if is_auth:
            return execute_personal_intent("loan_information", entities, customer_id)
        else:
            rates = get_interest_rates()
            return {
                "info": "We offer Home Loans (8.5%), Personal Loans (10.5%), and Car Loans (9.0%). Log in to view your active loans.",
                "rates": rates
            }

    elif intent == "emi_calculation":
        try:
            p = float(entities.get("principal", 500000))
        except (ValueError, TypeError):
            p = 500000.0
            
        try:
            r = float(entities.get("interest_rate", 8.5))
        except (ValueError, TypeError):
            r = 8.5
            
        try:
            t = int(entities.get("tenure_months", 60))
        except (ValueError, TypeError):
            t = 60
            
        emi_data = calculate_emi(p, r, t)
        return {"intent": "emi_calculation", "emi": emi_data, "principal": p, "rate": r, "tenure": t}

    elif intent == "interest_rate":
        rates = get_interest_rates()
        return {"intent": "interest_rate", "interest_rates": rates}

    elif intent == "spending_analysis":
        return execute_personal_intent("spending_analysis", entities, customer_id)

    elif intent == "fund_transfer":
        try:
            amount = float(entities.get("amount", 2000))
        except (ValueError, TypeError):
            amount = 2000.0
            
        recipient = entities.get("recipient", "Rahul")
        if not recipient:
            recipient = "Rahul"

        if amount <= 0:
            return {"error": "Transfer amount must be greater than zero."}

        # Check balance
        current_balance = get_balance(customer_id)
        if current_balance is None:
            return {"error": "Sender account not found."}
        if current_balance < amount:
            return {
                "error": f"Insufficient balance. Your current balance is ₹{current_balance:,.2f}, but requested transfer is ₹{amount:,.2f}."
            }

        # Fund transfer ALWAYS requires its own OTP challenge
        demo_otp = "123456"
        session["pending_transfer"] = {
            "recipient": recipient,
            "amount": amount,
            "otp": demo_otp
        }

        return {
            "intent": "fund_transfer",
            "action_required": "otp_verification",
            "scope": "fund_transfer",
            "amount": amount,
            "recipient": recipient,
            "demo_otp": demo_otp,
            "message": f"A verification OTP has been sent for transferring ₹{amount:,.2f} to {recipient}.\n\nDemo OTP: {demo_otp}\n\nPlease enter the OTP to complete the transfer."
        }

    elif intent == "banking_faq":
        topic = entities.get("topic", "general banking")
        rates = get_interest_rates()
        faqs = get_faqs()
        matched_faq = None
        for f in faqs:
            if topic.lower() in f.get("question", "").lower() or topic.lower() in f.get("topic", "").lower():
                matched_faq = f["answer"]
                break
        return {
            "intent": "banking_faq",
            "topic": topic,
            "info": matched_faq or "FinChat offers savings accounts, fixed deposits, home loans, car loans, and instant money transfers.",
            "rates": rates
        }

    elif intent in ["financial_advice", "savings_guidance"] or (intent == "general_assistance" and entities.get("topic") == "savings_guidance"):
        return {
            "intent": "financial_advice",
            "topic": "savings_guidance",
            "question": raw_text,
            "savings_rates": {
                "savings_account": "3.50% p.a.",
                "fixed_deposit": "6.00% - 7.00% p.a.",
                "recurring_deposit": "6.25% p.a."
            },
            "tips": [
                "Maintain a 3-6 month emergency fund in a high-liquidity Savings Account",
                "Use Fixed Deposits for locked-in guaranteed returns over 1 to 5 years",
                "Follow the 50/30/20 budgeting rule (50% needs, 30% wants, 20% savings)"
            ]
        }

    elif intent == "human_agent":
        return {
            "intent": "human_agent",
            "action": "connect_human",
            "message": "Demo: Request forwarded to a banking representative. A support officer will connect shortly."
        }

    else:
        return {
            "intent": "general_assistance",
            "question": raw_text,
            "info": "The user is asking a general banking question. Provide a helpful answer without inventing account-specific information."
        }
