import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_available = False

CANDIDATE_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3.5-flash"
]

if GEMINI_API_KEY and GEMINI_API_KEY != "your_api_key_here":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_available = True
    except Exception as e:
        print(f"Warning: Could not configure google.generativeai client: {e}")
        gemini_available = False

def generate_with_gemini(prompt: str) -> str | None:
    """Returns a Gemini text response, or None when the API is unavailable or limits exceeded."""
    if not gemini_available:
        return None

    try:
        import google.generativeai as genai
        for model_name in CANDIDATE_MODELS:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                err_str = str(e).lower()
                # If rate-limit (429) or high-demand (503), try next candidate
                if "429" in err_str or "quota" in err_str or "503" in err_str or "demand" in err_str or "404" in err_str or "not found" in err_str:
                    continue
                continue
    except Exception as ex:
        print(f"Gemini generation error: {ex}")
    return None

def detect_language(text: str) -> str:
    """Detects if input text is in Kannada script, Hindi script, or English"""
    if any("\u0c80" <= c <= "\u0cff" for c in text):
        return "kannada"
    if any("\u0900" <= c <= "\u097f" for c in text):
        return "hindi"
    return "english"

def rule_based_fallback_intent(user_input: str, is_authenticated: bool) -> dict:
    """
    High-reliability rule-based intent & entity extractor supporting
    both English and Kannada queries. Used when Gemini API is unavailable,
    unconfigured, or fails.
    """
    text = user_input.lower().strip()
    normalized_text = re.sub(r"[^\w\s]", "", text).strip()

    # 1. Greetings and conversational openers. These are deliberately checked
    # before task intents so a simple "hi" never falls through to escalation.
    greeting_phrases = {
        "hi", "hello", "hey", "hii", "hiii", "good morning",
        "good afternoon", "good evening", "namaste", "ನಮಸ್ಕಾರ",
        "ನಮಸ್ತೆ", "ಹಾಯ್", "ಹಲೋ"
    }
    casual_greeting_patterns = [
        r"^(?:hi|hello|hey|hii|hiii)\s+(?:how are you|how r you|whats up|what is up|there|finchat|assistant|bot)$",
        r"^(?:good morning|good afternoon|good evening)\s+(?:finchat|assistant|team)?$",
    ]
    if (
        normalized_text in greeting_phrases
        or any(re.fullmatch(pattern, normalized_text) for pattern in casual_greeting_patterns)
    ):
        return {"intent": "greeting", "entities": {}}
    
    # 2. Human agent escalation
    if any(k in text for k in ["human", "agent", "representative", "manager", "support executive", "ಮಾನವ", "ಪ್ರತಿನಿಧಿ"]):
        return {"intent": "human_agent", "entities": {}}
        
    # 3. Fund transfer
    # Supports: "Transfer ₹2000 to Rahul", "send 500 to Priya", "ವರ್ಗಾವಣೆ", "ಕಳುಹಿಸು"
    transfer_keywords = ["transfer", "send money", "pay", "remit", "ವರ್ಗಾಯಿಸು", "ಕಳುಹಿಸು", "ವರ್ಗಾವಣೆ"]
    if any(k in text for k in transfer_keywords):
        amount = None
        recipient = None
        
        # Extract amount: ₹2000, 2,000, 2000, 2000 rs, rs 2000
        amt_match = re.search(r'(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)\s*(?:₹|rs\.?|inr|rupees)?', text)
        if amt_match:
            try:
                amt_str = amt_match.group(1).replace(",", "")
                amount = float(amt_str)
            except Exception:
                pass
                
        # Extract recipient: "to <name>", "for <name>", "<name> ge"
        to_match = re.search(r'(?:to|for)\s+([a-zA-Z]+)', user_input, re.IGNORECASE)
        if to_match:
            recipient = to_match.group(1).strip()
        else:
            # Kannada: "<name> ge" or "<name> rige"
            kannada_to = re.search(r'([a-zA-Z\u0c80-\u0cff]+)(?:ಗೆ|ರಿಗೆ|ಗೆ)\s+(?:₹|\d+)', user_input)
            if kannada_to:
                recipient = kannada_to.group(1).strip()
            elif "rahul" in text or "ರಾಹುಲ್" in text:
                recipient = "Rahul"
            elif "priya" in text or "ಪ್ರಿಯಾ" in text:
                recipient = "Priya"
            elif "suresh" in text or "ಸುರೇಶ್" in text:
                recipient = "Suresh"
            elif "ananya" in text or "ಅನನ್ಯ" in text:
                recipient = "Ananya"
            elif "vikram" in text or "ವಿಕ್ರಮ್" in text:
                recipient = "Vikram"
                
        return {
            "intent": "fund_transfer",
            "entities": {
                "amount": amount or 2000,
                "recipient": recipient or "Rahul"
            }
        }
        
    # 3. Balance enquiry
    # Supports: "What is my balance?", "how much money do i have", "ನನ್ನ ಬ್ಯಾಲೆನ್ಸ್ ಎಷ್ಟು?"
    balance_keywords = ["balance", "bal", "how much money", "account balance", "ಬ್ಯಾಲೆನ್ಸ್", "ಹಣವೆಷ್ಟು", "ಬಾಕಿ"]
    if any(k in text for k in balance_keywords):
        return {"intent": "balance_enquiry", "entities": {}}
        
    # 4. Spending analysis
    # Supports: "Where am I spending most?", "spending analysis", "analyze spending", "ಖರ್ಚು", "ವೆಚ್ಚ"
    spending_keywords = [
        "spending", "spend", "expense", "expenses", "where am i spending",
        "statistics", "statistic", "stats", "statistical report", "statistic report",
        "spending report", "account report", "account summary", "financial summary", "analysis",
        "ಖರ್ಚು", "ವೆಚ್ಚ"
    ]
    if any(k in text for k in spending_keywords):
        least_spending_terms = ["least", "lest", "lowest", "minimum", "smallest", "least spent"]
        focus = "least" if any(term in text for term in least_spending_terms) else "highest"
        return {"intent": "spending_analysis", "entities": {"focus": focus}}
        
    # 5. Transaction history
    # Supports: "Show my recent transactions", "mini statement", "passbook", "ವ್ಯವಹಾರ", "ಖರ್ಚುಗಳ ಪಟ್ಟಿ"
    txn_keywords = ["transaction", "transactions", "statement", "passbook", "history", "ವ್ಯವಹಾರ", "ವ್ಯವಹಾರಗಳನ್ನು"]
    if any(k in text for k in txn_keywords):
        return {"intent": "transaction_history", "entities": {}}
        
    # 6. EMI calculation
    # Supports: "Calculate EMI for ₹5 lakh loan", "emi for 500000", "ಇಎಂಐ"
    if "emi" in text or "ಇಎಂಐ" in text or "calculator" in text or "ಗಣನೆ" in text:
        principal = 500000.0
        tenure = 60
        rate = 8.5
        
        # Check for numbers in text
        nums = re.findall(r'(\d+(?:\.\d+)?)\s*(lakh|lac|k|thousand|months|years|month|year)?', text)
        for num, unit in nums:
            val = float(num)
            if unit in ["lakh", "lac"]:
                principal = val * 100000
            elif unit in ["k", "thousand"]:
                principal = val * 1000
            elif unit in ["year", "years"]:
                tenure = int(val * 12)
            elif unit in ["month", "months"]:
                tenure = int(val)
            elif val > 10000:
                principal = val
                
        return {
            "intent": "emi_calculation",
            "entities": {
                "principal": principal,
                "interest_rate": rate,
                "tenure_months": tenure
            }
        }
        
    # 7. Loan information / inquiry
    loan_keywords = ["loan", "home loan", "personal loan", "car loan", "ಸಾಲ", "ಲೋನ್"]
    if any(k in text for k in loan_keywords):
        if "rate" in text or "interest" in text or "ಬಡ್ಡಿ" in text:
            return {"intent": "interest_rate", "entities": {"topic": "loan"}}
        if is_authenticated:
            return {"intent": "loan_information", "entities": {}}
        return {"intent": "banking_faq", "entities": {"topic": "loans"}}

    # 8. Interest rate
    rate_keywords = ["interest", "interest rate", "fd rate", "rate of interest", "ಬಡ್ಡಿ", "ಬಡ್ಡಿದರ"]
    if any(k in text for k in rate_keywords):
        return {"intent": "interest_rate", "entities": {}}
        
    # 9. Account details
    account_keywords = ["account details", "my account", "account number", "profile", "ಖಾತೆ ವಿವರ"]
    if any(k in text for k in account_keywords):
        return {"intent": "account_details", "entities": {}}

    # 10. General savings and money-management guidance. These questions are
    # intentionally sent to Gemini for a conversational answer; they do not
    # trigger a private account lookup or any banking transaction.
    advisory_keywords = [
        "save my money", "saving money", "where can i save", "where should i save",
        "how should i save", "how can i save", "save money", "grow my money",
        "investment options", "invest my money", "invest money", "where to invest",
        "financial guidance", "money advice", "saving options", "financial advice",
        "ಉಳಿತಾಯ", "ಹಣ ಉಳಿಸುವುದು", "ಹೂಡಿಕೆ", "ಹಣವನ್ನು ಎಲ್ಲಿ ಉಳಿಸಬಹುದು", "ಹಣ ಉಳಿಸಲು"
    ]
    if any(k in text for k in advisory_keywords):
        return {"intent": "financial_advice", "entities": {"topic": "savings_guidance"}}
        
    # 11. General FAQ
    faq_keywords = ["how to", "procedure", "how does", "open account", "block card", "ಹೇಗೆ", "ತೆರೆಯುವುದು"]
    if any(k in text for k in faq_keywords):
        return {"intent": "banking_faq", "entities": {"topic": "general"}}
        
    # Unknown
    return {"intent": "unknown", "entities": {}}

def get_intent_and_entities(user_input: str, is_authenticated: bool) -> dict:
    """
    Extracts intent and entities using Gemini API with intelligent fallback.
    """
    # Keep common greetings deterministic rather than relying on a remote
    # classifier, which may otherwise label them as "unknown".
    local_intent = rule_based_fallback_intent(user_input, is_authenticated)
    if local_intent["intent"] == "greeting":
        return local_intent

    if gemini_available:
        prompt = f"""
        You are an accurate intent classifier for a retail banking assistant.
        The user is currently {'authenticated' if is_authenticated else 'NOT authenticated'}.
        Extract the user intent and relevant entities from the query (which may be in English or Kannada).
        
        Valid intents:
        - balance_enquiry
        - transaction_history
        - account_details
        - loan_information
        - emi_calculation
        - interest_rate
        - spending_analysis
        - fund_transfer
        - banking_faq
        - financial_advice (for questions about saving money, investing, growing savings, budgeting, or savings options)
        - human_agent
        - greeting (for simple greetings such as "hi", "hello", or "namaste")
        - general_assistance (for normal banking-related questions that do not fit another intent)
        - unknown
        
        Extraction guidelines:
        - emi_calculation: extract 'principal' (number), 'interest_rate' (number), 'tenure_months' (integer). Defaults: principal: 500000, rate: 8.5, tenure: 60.
        - fund_transfer: extract 'amount' (number) and 'recipient' (string).
        - banking_faq: extract 'topic' (string).
        - spending_analysis: extract 'focus' as 'highest' or 'least' when the user asks which category they spend the most or least on.
        - financial_advice: extract 'topic' as 'savings_guidance'.
        - Use general_assistance instead of unknown for conversational or banking-related requests.
        
        Respond ONLY with a JSON object. No markdown, no backticks.
        Format:
        {{
          "intent": "...",
          "entities": {{...}}
        }}
        
        User Query: "{user_input}"
        """
        try:
            clean_text = generate_with_gemini(prompt)
            if not clean_text:
                raise ValueError("Gemini returned an empty intent response")
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3]
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3]
            data = json.loads(clean_text.strip())
            if "intent" in data:
                if local_intent["intent"] == "financial_advice":
                    data["intent"] = "financial_advice"
                    data.setdefault("entities", {})["topic"] = "savings_guidance"
                    return data
                if (
                    data["intent"] in {"unknown", "general_assistance"}
                    and local_intent["intent"] != "unknown"
                ):
                    return local_intent
                if (
                    data["intent"] == "banking_faq"
                    and local_intent["intent"] in {"general_assistance", "financial_advice"}
                ):
                    return local_intent
                if data["intent"] == "spending_analysis" and local_intent["intent"] == "spending_analysis":
                    # Prefer the explicit wording detected locally (for
                    # example, "least" or the common typo "lest").
                    data.setdefault("entities", {})["focus"] = local_intent["entities"].get("focus", "highest")
                return data
        except Exception as e:
            print(f"Gemini Intent Detection API call error: {e}. Switching to rule-based parser.")
            
    # Fallback to rule engine
    return rule_based_fallback_intent(user_input, is_authenticated)

def generate_natural_response(intent: str, data: dict, language: str = "english", conversation_history: list = None) -> str:
    """
    Generates natural language response using Gemini API with rich Kannada & English fallback templates.
    """
    if gemini_available:
        if intent in ["financial_advice", "savings_guidance"] or data.get("topic") == "savings_guidance":
            user_question = data.get("question") or "where can i save my money"
            prompt = f"""
            You are a polite, helpful, and knowledgeable AI banking assistant for FinChat Bank.
            The user asks: "{user_question}"
            
            Provide a clear, well-structured, and practical advisory response strictly in {language.upper()} language (if language is 'kannada', write entirely in natural Kannada script):
            1. Introduce FinChat Bank's core savings & deposit options:
               - FinChat Savings Account: 3.50% interest p.a., 24/7 liquidity, ideal for everyday money and emergency funds.
               - FinChat Fixed Deposits (FD): 6.00% to 7.00% p.a. guaranteed returns across tenures from 1 to 5 years (1 yr: 6.0%, 3 yrs: 6.5%, 5 yrs: 7.0%).
               - FinChat Recurring Deposits (RD): disciplined monthly deposits with attractive interest rates.
            2. Share practical financial wisdom:
               - Build an emergency reserve covering 3 to 6 months of living expenses in an accessible Savings Account.
               - Apply the 50/30/20 budgeting framework (50% needs, 30% wants, 20% savings).
            3. Include a friendly, non-guaranteed financial awareness disclaimer.
            4. If language is 'kannada', write the entire response fluently in Kannada script.
            
            Response:
            """
        else:
            prompt = f"""
            You are a polite, helpful AI banking assistant for FinChat Bank.
            Provide a natural, concise, professional response based on the following verified data.
            
            CRITICAL RULES:
            1. ONLY use information from the provided Data. NEVER invent balances, account numbers, or transaction IDs.
            2. Respond strictly in {language.upper()} language. If language is 'kannada', respond in natural Kannada script.
            3. For spending analysis, mention the monthly spending, top category, and a friendly, non-guaranteed saving tip.
            4. For fund transfer requiring OTP, state that a verification OTP has been sent (Demo OTP: 123456).
            5. For spending analysis, honor Data.focus exactly: when it is 'least', answer with the lowest-spending category; otherwise answer with the highest-spending category.
            6. For general_assistance, answer Data.question directly with practical, general banking guidance. For savings questions, briefly explain suitable options such as a savings account, fixed deposit, or recurring deposit and their trade-offs. Do not fabricate rates, recommend a specific product as personalized financial advice, or send the user to a human agent.
            
            Intent: {intent}
            Data: {json.dumps(data, ensure_ascii=False)}
            Language: {language}

            For general_assistance, answer the user's question in Data.question directly.
            Do not redirect the user to a human agent unless the intent is human_agent.
            
            Response:
            """
        try:
            response_text = generate_with_gemini(prompt)
            if response_text:
                return response_text
        except Exception as e:
            print(f"Gemini Generation API call error: {e}. Switching to local template response.")

    # High quality fallback responses for English and Kannada
    return generate_fallback_response(intent, data, language)

def generate_fallback_response(intent: str, data: dict, language: str = "english") -> str:
    """Generates rich, accurate responses when Gemini API is offline or unconfigured."""
    is_kn = (language.lower() == "kannada")

    if data.get("action_required") == "otp_verification":
        scope = data.get("scope", "fund_transfer")
        if scope == "personal_data":
            if is_kn:
                return "🔒 ಭದ್ರತಾ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ:\nನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಹಣಕಾಸಿನ ವಿವರಗಳನ್ನು ವೀಕ್ಷಿಸಲು ನಿಮ್ಮ ನೋಂದಾಯಿತ ಮೊಬೈಲ್ ಸಂಖ್ಯೆಗೆ (98XXXXXX21) ಪರಿಶೀಲನಾ OTP ಕಳುಹಿಸಲಾಗಿದೆ.\n\nಡೆಮೊ OTP: 123456\n\nದಯವಿಟ್ಟು ಮುಂದುವರಿಯಲು OTP ನಮೂದಿಸಿ."
            return "🔒 Security Verification Required:\nTo access your personal financial information, a verification OTP has been sent to your registered mobile (98XXXXXX21).\n\nDemo OTP: 123456\n\nPlease enter the OTP to view your account details."
        else:
            amt = data.get("amount", 2000)
            rec = data.get("recipient", "Rahul")
            if is_kn:
                return f"{rec} ಅವರಿಗೆ ₹{amt:,.2f} ವರ್ಗಾಯಿಸಲು ಪರಿಶೀಲನಾ OTP ಕಳುಹಿಸಲಾಗಿದೆ.\n\nಡೆಮೊ OTP: 123456\n\nವರ್ಗಾವಣೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲು ದಯವಿಟ್ಟು OTP ನಮೂದಿಸಿ."
            return f"A verification OTP has been sent for transferring ₹{amt:,.2f} to {rec}.\n\nDemo OTP: 123456\n\nPlease enter the OTP to complete the transfer."

    if "error" in data:
        err = data["error"]
        if "Please log in first" in err:
            return "ನಿಮ್ಮ ವೈಯಕ್ತಿಕ ಖಾತೆಯ ಮಾಹಿತಿಯನ್ನು ಪ್ರವೇಶಿಸಲು ದಯವಿಟ್ಟು ಮೊದಲು ಲಾಗಿನ್ ಮಾಡಿ." if is_kn else "Please log in first to access your personal account information."
        return f"ಕ್ಷಮಿಸಿ: {err}" if is_kn else f"Notice: {err}"

    prefix = ""
    if data.get("otp_verified_now"):
        prefix = "✅ OTP ಪರಿಶೀಲನೆ ಯಶಸ್ವಿಯಾಗಿದೆ!\n\n" if is_kn else "✅ OTP Verified Successfully!\n\n"

    if intent == "greeting":
        if is_kn:
            return "ನಮಸ್ಕಾರ! ನಾನು FinChat ಬ್ಯಾಂಕಿಂಗ್ ಸಹಾಯಕ. ಬ್ಯಾಲೆನ್ಸ್, ಇತ್ತೀಚಿನ ವಹಿವಾಟುಗಳು, ಖರ್ಚಿನ ಮಾಹಿತಿ, ಸಾಲ, EMI ಅಥವಾ ಹಣ ವರ್ಗಾವಣೆ ಕುರಿತು ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?"
        return "Hello! I'm your FinChat banking assistant. I can help with balances, recent transactions, spending insights, loans, EMI, or money transfers. How can I help today?"

    if intent == "balance_enquiry":
        bal = data.get("balance", 0)
        if is_kn:
            return prefix + f"ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಉಳಿತಾಯ ಖಾತೆಯ ಬಾಕಿ ₹{bal:,.2f} ಆಗಿದೆ."
        return prefix + f"Your current available balance is ₹{bal:,.2f}."

    elif intent == "transaction_history":
        txns = data.get("transactions", [])
        if not txns:
            return "ಯಾವುದೇ ಇತ್ತೀಚಿನ ವ್ಯವಹಾರಗಳು ಕಂಡುಬಂದಿಲ್ಲ." if is_kn else "No recent transactions found."
        
        if is_kn:
            lines = ["ನಿಮ್ಮ ಇತ್ತೀಚಿನ ವ್ಯವಹಾರಗಳು ಇಲ್ಲಿವೆ:"]
            for t in txns[:5]:
                sign = "-" if t.get("type") == "debit" else "+"
                lines.append(f"• {t.get('date')}: {t.get('description')} ({t.get('category')}) {sign}₹{t.get('amount'):,.2f}")
            return "\n".join(lines)
        else:
            lines = ["Here are your recent transactions:"]
            for t in txns[:5]:
                sign = "-" if t.get("type") == "debit" else "+"
                lines.append(f"• {t.get('date')}: {t.get('description')} ({t.get('category')}) {sign}₹{t.get('amount'):,.2f}")
            return "\n".join(lines)

    elif intent == "account_details":
        acc = data.get("account", {})
        if is_kn:
            return (f"ಖಾತೆ ವಿವರಗಳು:\n"
                    f"• ಹೆಸರು: {acc.get('name')}\n"
                    f"• ಖಾತೆ ಸಂಖ್ಯೆ: {acc.get('account_number')}\n"
                    f"• ಖಾತೆ ಪ್ರಕಾರ: {acc.get('account_type')}\n"
                    f"• ಮೊಬೈಲ್: {acc.get('mobile')}\n"
                    f"• ಪ್ರಸ್ತುತ ಬ್ಯಾಲೆನ್ಸ್: ₹{acc.get('balance', 0):,.2f}")
        return (f"Here are your account details:\n"
                f"• Account Holder: {acc.get('name')}\n"
                f"• Account Number: {acc.get('account_number')}\n"
                f"• Account Type: {acc.get('account_type')}\n"
                f"• Registered Mobile: {acc.get('mobile')}\n"
                f"• Current Balance: ₹{acc.get('balance', 0):,.2f}")

    elif intent == "loan_information":
        loans = data.get("loans", [])
        if not loans:
            return "ನಿಮ್ಮ ಖಾತೆಯಲ್ಲಿ ಸಕ್ರಿಯ ಸಾಲಗಳಿಲ್ಲ." if is_kn else "You have no active loans linked to this account."
        
        if is_kn:
            lines = ["ನಿಮ್ಮ ಸಕ್ರಿಯ ಸಾಲದ ಮಾಹಿತಿ:"]
            for l in loans:
                lines.append(f"• {l.get('type')}: ಸಾಲದ ಮೊತ್ತ ₹{l.get('principal_amount'):,.2f}, ಬಾಕಿ ಮೊತ್ತ ₹{l.get('outstanding_amount'):,.2f}, ಬಡ್ಡಿದರ {l.get('interest_rate')}%, ಮಾಸಿಕ EMI ₹{l.get('emi'):,.2f}")
            return "\n".join(lines)
        else:
            lines = ["Here are your active loan details:"]
            for l in loans:
                lines.append(f"• {l.get('type')}: Principal ₹{l.get('principal_amount'):,.2f}, Outstanding ₹{l.get('outstanding_amount'):,.2f}, Interest Rate {l.get('interest_rate')}%, Monthly EMI ₹{l.get('emi'):,.2f}")
            return "\n".join(lines)

    elif intent == "emi_calculation":
        emi = data.get("emi", {})
        if isinstance(emi, dict):
            m_emi = emi.get("monthly_emi", 0)
            p = emi.get("principal", 0)
            r = emi.get("interest_rate", 0)
            t = emi.get("tenure_months", 0)
            tot_int = emi.get("total_interest", 0)
            tot_pay = emi.get("total_payment", 0)
        else:
            m_emi = emi
            p = data.get("principal", 500000)
            r = data.get("rate", 8.5)
            t = data.get("tenure", 60)
            tot_int = round(m_emi * t - p, 2)
            tot_pay = round(m_emi * t, 2)

        if is_kn:
            return (f"₹{p:,.2f} ಸಾಲಕ್ಕಾಗಿ {r}% ಬಡ್ಡಿದರದಲ್ಲಿ {t} ತಿಂಗಳುಗಳಿಗೆ ಗಣನೆ ಮಾಡಲಾದ ಇಎಂಐ:\n"
                    f"• ಮಾಸಿಕ ಇಎಂಐ (Monthly EMI): ₹{m_emi:,.2f}\n"
                    f"• ಒಟ್ಟು ಬಡ್ಡಿ (Total Interest): ₹{tot_int:,.2f}\n"
                    f"• ಒಟ್ಟು ಮರುಪಾವತಿ (Total Payment): ₹{tot_pay:,.2f}")
        return (f"EMI calculation for ₹{p:,.2f} at {r}% interest for {t} months:\n"
                f"• Monthly EMI: ₹{m_emi:,.2f}\n"
                f"• Total Interest Payable: ₹{tot_int:,.2f}\n"
                f"• Total Repayment: ₹{tot_pay:,.2f}")

    elif intent == "interest_rate":
        rates = data.get("interest_rates", {})
        fd = rates.get("fixed_deposit", {})
        if is_kn:
            return (f"ನಮ್ಮ ಪ್ರಸ್ತುತ ಬಡ್ಡಿದರಗಳು:\n"
                    f"• ಉಳಿತಾಯ ಖಾತೆ: {rates.get('savings_account', 3.5)}%\n"
                    f"• ಗೃಹ ಸಾಲ (Home Loan): {rates.get('home_loan', 8.5)}% ರಿಂದ ಪ್ರಾರಂಭ\n"
                    f"• ವೈಯಕ್ತಿಕ ಸಾಲ (Personal Loan): {rates.get('personal_loan', 10.5)}%\n"
                    f"• ವಾಹನ ಸಾಲ (Car Loan): {rates.get('car_loan', 9.0)}%\n"
                    f"• ಫಿಕ್ಸೆಡ್ ಡೆಪಾಸಿಟ್ (FD): 1 ವರ್ಷ - {fd.get('1_year', 6.0)}%, 3 ವರ್ಷ - {fd.get('3_years', 6.5)}%, 5 ವರ್ಷ - {fd.get('5_years', 7.0)}%")
        return (f"Here are our current interest rates:\n"
                f"• Savings Account: {rates.get('savings_account', 3.5)}% p.a.\n"
                f"• Home Loan: Starting from {rates.get('home_loan', 8.5)}% p.a.\n"
                f"• Personal Loan: {rates.get('personal_loan', 10.5)}% p.a.\n"
                f"• Car Loan: {rates.get('car_loan', 9.0)}% p.a.\n"
                f"• Fixed Deposits (FD): 1 Yr: {fd.get('1_year', 6.0)}%, 3 Yrs: {fd.get('3_years', 6.5)}%, 5 Yrs: {fd.get('5_years', 7.0)}%")

    elif intent == "spending_analysis":
        tot = data.get("monthly_spending", 0)
        cats = data.get("categories", {})
        focus = data.get("focus", "highest")
        category = (
            min(cats, key=cats.get) if focus == "least" and cats
            else data.get("largest_category", "None")
        )
        category_amount = cats.get(category, 0)
        category_share = (category_amount / tot * 100) if tot else 0

        if is_kn:
            qualifier = "ಕಡಿಮೆ" if focus == "least" else "ಹೆಚ್ಚು"
            return (f"ನಿಮ್ಮ {qualifier} ಖರ್ಚು {category} ಮೇಲೆ ಆಗಿದೆ: "
                    f"₹{category_amount:,.2f} ({category_share:.0f}% of ₹{tot:,.2f}).\n\n"
                    f"ವಿವರವಾದ ಖರ್ಚಿನ ಸಾರಾಂಶವನ್ನು ಕೆಳಗಿನ ಕಾರ್ಡ್‌ನಲ್ಲಿ ನೋಡಿ.")
        qualifier = "lowest" if focus == "least" else "highest"
        return (f"Your {qualifier} spending was on {category}: "
                f"₹{category_amount:,.2f} ({category_share:.0f}% of your ₹{tot:,.2f} monthly spending).\n\n"
                f"See the card below for the full category breakdown.")

    elif intent == "fund_transfer":
        if data.get("action_required") == "otp_verification":
            amt = data.get("amount", 0)
            rec = data.get("recipient", "")
            if is_kn:
                return f"{rec} ಅವರಿಗೆ ₹{amt:,.2f} ವರ್ಗಾಯಿಸಲು ಪರಿಶೀಲನಾ OTP ಕಳುಹಿಸಲಾಗಿದೆ.\n\nಡೆಮೊ OTP: 123456\n\nವರ್ಗಾವಣೆಯನ್ನು ಪೂರ್ಣಗೊಳಿಸಲು ದಯವಿಟ್ಟು OTP ನಮೂದಿಸಿ."
            return f"A verification OTP has been sent for transferring ₹{amt:,.2f} to {rec}.\n\nDemo OTP: 123456\n\nPlease enter the OTP to complete the transfer."
        elif data.get("success"):
            amt = data.get("amount", 0)
            rec = data.get("recipient", "")
            rem = data.get("remaining_balance", 0)
            if is_kn:
                return f"ಹಣ ವರ್ಗಾವಣೆ ಯಶಸ್ವಿಯಾಗಿದೆ!\n\n{rec} ಅವರಿಗೆ ₹{amt:,.2f} ಯಶಸ್ವಿಯಾಗಿ ಕಳುಹಿಸಲಾಗಿದೆ.\nನಿಮ್ಮ ಉಳಿದ ಖಾತೆ ಬ್ಯಾಲೆನ್ಸ್: ₹{rem:,.2f}"
            return f"Transfer successful!\n\n₹{amt:,.2f} has been transferred to {rec}.\nRemaining balance: ₹{rem:,.2f}"
        else:
            return data.get("message", "Transfer processed.")

    elif intent == "banking_faq":
        rates = data.get("rates", {})
        info = data.get("info", "")
        if "home loan" in str(data).lower():
            if is_kn:
                return f"ನಮ್ಮ ಗೃಹ ಸಾಲದ (Home Loan) ಬಡ್ಡಿದರಗಳು ವಾರ್ಷಿಕ 8.5% ರಿಂದ ಪ್ರಾರಂಭವಾಗುತ್ತವೆ ಮತ್ತು 30 ವರ್ಷಗಳವರೆಗೆ ಮರುಪಾವತಿ ಅವಧಿ ಲಭ್ಯವಿದೆ."
            return f"Our home loan interest rates start at 8.5% per annum with repayment tenures up to 30 years and attractive terms."
        if is_kn:
            return f"ಬ್ಯಾಂಕಿಂಗ್ ಮಾಹಿತಿ: {info}\nಹೆಚ್ಚಿನ ವಿವರಗಳಿಗಾಗಿ ದಯವಿಟ್ಟು ನಮ್ಮ ಶಾಖೆ ಅಥವಾ ಗ್ರಾಹಕ ಸಹಾಯವಾಣಿಯನ್ನು ಸಂಪರ್ಕಿಸಿ."
        return f"Banking Information: {info}\nFeel free to ask about loans, fixed deposits, interest rates, or EMI calculations!"

    elif intent == "human_agent":
        if is_kn:
            return "ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ನಾನು ಆತ್ಮವಿಶ್ವಾಸದಿಂದ ಪರಿಹರಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ನೀವು ನಮ್ಮ ಬ್ಯಾಂಕಿಂಗ್ ಪ್ರತಿನಿಧಿಯೊಂದಿಗೆ ಸಂಪರ್ಕ ಸಾಧಿಸಲು ಬಯಸುವಿರಾ?\n\n[ಡೆಮೊ: ವಿನಂತಿಯನ್ನು ಗ್ರಾಹಕ ಪ್ರತಿನಿಧಿಗೆ ರವಾನಿಸಲಾಗಿದೆ.]"
        return "I couldn't confidently resolve your request. Would you like to connect with a banking representative?\n\nDemo: Request forwarded to a banking representative."

    elif intent in ["financial_advice", "savings_guidance"] or data.get("topic") == "savings_guidance":
        if is_kn:
            return (
                "ನಮಸ್ಕಾರ! ಫಿನ್‌ಚಾಟ್ ಬ್ಯಾಂಕ್‌ನಲ್ಲಿ ನಿಮ್ಮ ಹಣವನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ಮತ್ತು ಲಾಭದಾಯಕವಾಗಿ ಉಳಿಸಲು ಉತ್ತಮ ಆಯ್ಕೆಗಳು ಇಲ್ಲಿವೆ:\n\n"
                "1. **ಫಿನ್‌ಚಾಟ್ ಉಳಿತಾಯ ಖಾತೆ (Savings Account):** ವಾರ್ಷಿಕ 3.5% ಬಡ್ಡಿ ದರ, 24/7 ತಕ್ಷಣದ ಹಣದ ಲಭ್ಯತೆ. ದೈನಂದಿನ ಖರ್ಚು ಮತ್ತು ತುರ್ತು ನಿಧಿಗೆ ಸೂಕ್ತ.\n"
                "2. **ಫಿಕ್ಸೆಡ್ ಡೆಪಾಸಿಟ್ (FD):** ವಾರ್ಷಿಕ 6.0% ರಿಂದ 7.0% ವರೆಗೆ ಖಾತರಿಯ ಲಾಭ (1 ವರ್ಷ: 6.0%, 3 ವರ್ಷ: 6.5%, 5 ವರ್ಷ: 7.0%).\n"
                "3. **ರೆಕರಿಂಗ್ ಡೆಪಾಸಿಟ್ (RD):** ಶಿಸ್ತುಬದ್ಧ ಮಾಸಿಕ ಉಳಿತಾಯಕ್ಕೆ 6.25% ವರೆಗೆ ಆಕರ್ಷಕ ಬಡ್ಡಿ.\n\n"
                "💡 **ಸ್ಮಾರ್ಟ್ ಉಳಿತಾಯ ಸಲಹೆಗಳು:**\n"
                "• 3 ರಿಂದ 6 ತಿಂಗಳ ಖರ್ಚಿಗೆ ಸಮನಾದ ತುರ್ತು ನಿಧಿಯನ್ನು (Emergency Fund) ಉಳಿತಾಯ ಖಾತೆಯಲ್ಲಿ ಇರಿಸಿ.\n"
                "• 50/30/20 ಬಜೆಟ್ ನಿಯಮವನ್ನು ಪಾಲಿಸಿ (50% ಅಗತ್ಯತೆ, 30% ಇಷ್ಟಗಳು, 20% ಉಳಿತಾಯ).\n\n"
                "⚠️ *ಗಮನಿಸಿ: ಇದು ಸಾಮಾನ್ಯ ಹಣಕಾಸು ಜಾಗೃತಿ ಮಾಹಿತಿಯಾಗಿದೆ.*"
            )
        return (
            "Here are the best ways to save and grow your money with FinChat Bank:\n\n"
            "1. **FinChat Savings Account:** 3.50% p.a. interest with instant 24/7 liquidity. Best for everyday expenses and emergency funds.\n"
            "2. **Fixed Deposits (FD):** Guaranteed returns from 6.00% to 7.00% p.a. with flexible tenures from 1 to 5 years (1 Yr: 6.0%, 3 Yrs: 6.5%, 5 Yrs: 7.0%).\n"
            "3. **Recurring Deposits (RD):** Disciplined monthly savings yielding up to 6.25% p.a.\n\n"
            "💡 **Smart Financial Principles:**\n"
            "• **Emergency Fund:** Keep 3 to 6 months of living expenses in an accessible savings account.\n"
            "• **50/30/20 Rule:** Allocate 50% of income to Needs, 30% to Wants, and 20% to Savings/Investments.\n\n"
            "⚠️ *Note: This guidance is for financial awareness and educational purposes.*"
        )

    elif intent == "general_assistance":
        if is_kn:
            return "ನಾನು ಸಹಾಯ ಮಾಡಲು ಸಿದ್ಧನಿದ್ದೇನೆ. ಬ್ಯಾಲೆನ್ಸ್, ಇತ್ತೀಚಿನ ವಹಿವಾಟುಗಳು, ಖರ್ಚಿನ ವರದಿ, ಸಾಲ, EMI, ಬಡ್ಡಿದರ ಅಥವಾ ಹಣ ವರ್ಗಾವಣೆ ಕುರಿತು ಕೇಳಬಹುದು."
        return "I'm here to help with your banking questions. You can ask about balances, recent transactions, spending reports, loans, EMI, interest rates, or money transfers."

    else:
        if is_kn:
            return "ಕ್ಷಮಿಸಿ, ನಿಮ್ಮ ವಿನಂತಿಯನ್ನು ನಾನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ನೀವು ಬ್ಯಾಲೆನ್ಸ್, ವಹಿವಾಟುಗಳು, ಸಾಲಗಳು, ಇಎಂಐ ಅಥವಾ ಹಣ ವರ್ಗಾವಣೆ ಬಗ್ಗೆ ಕೇಳಬಹುದು."
        return "I'm sorry, I couldn't understand that request. You can ask me about account balance, recent transactions, spending analysis, loans, interest rates, EMI calculations, or fund transfers."
