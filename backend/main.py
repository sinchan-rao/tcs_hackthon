from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json

from backend.banking_service import (
    get_balance, get_transactions, get_account_details,
    get_loan_information, calculate_emi, get_interest_rates,
    analyze_spending, transfer_money, load_data
)
from backend.gemini_service import (
    get_intent_and_entities, generate_natural_response, detect_language
)
from backend.intent_handler import handle_intent, get_session
from backend.session_manager import COOKIE_NAME, session_manager
from backend.conversation_manager import conversation_manager

app = FastAPI(title="FinChat — AI-Powered Conversational Banking Assistant")

# Allow credentials for session cookies — must use explicit origins (not *)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class LoginRequest(BaseModel):
    customer_id: str
    pin: str

class EMIRequest(BaseModel):
    principal: float
    interest_rate: float
    tenure_months: int

class ChatRequest(BaseModel):
    text: str
    customer_id: str | None = None

class ConversationMessageRequest(BaseModel):
    role: str
    content: str

class TransferInitiateRequest(BaseModel):
    customer_id: str
    recipient: str
    amount: float

class TransferVerifyRequest(BaseModel):
    customer_id: str
    recipient: str
    amount: float
    otp: str

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "FinChat Banking Assistant API",
        "version": "1.0.0"
    }


def get_browser_session(request: Request, response: Response):
    """Resolve the opaque cookie to server-side session and conversation IDs."""
    cookie_session_id = request.cookies.get(COOKIE_NAME)
    persisted_conversation = conversation_manager.find_by_session(cookie_session_id)

    if persisted_conversation and cookie_session_id:
        record = session_manager.restore_session(
            session_id=cookie_session_id,
            conversation_id=persisted_conversation["conversation_id"],
            created_at=persisted_conversation["created_at"],
        )
        created = False
    else:
        record, created = session_manager.ensure_session(cookie_session_id)

    conversation_manager.ensure_conversation(record.session_id, record.conversation_id)
    if created:
        session_manager.set_session_cookie(response, record.session_id)
    return record, created


@app.post("/session/create")
def create_or_restore_session(request: Request, response: Response):
    """Create the first browser session or report the current one.

    Session and conversation identifiers are deliberately not returned in JSON.
    """
    _, created = get_browser_session(request, response)
    return {
        "created": created,
        "message": "Browser session ready",
    }


@app.get("/conversation/history")
def get_conversation_history(request: Request, response: Response):
    """Return the safe, persisted messages for this browser's conversation."""
    record, created = get_browser_session(request, response)
    messages = conversation_manager.get_messages(record.conversation_id)
    return {
        "restored": bool(messages) and not created,
        "messages": messages,
    }


@app.post("/conversation/message")
def save_conversation_message(
    message: ConversationMessageRequest, request: Request, response: Response
):
    """Save a non-banking message through the same privacy-safe storage path."""
    record, _ = get_browser_session(request, response)
    conversation_manager.append_message(record.conversation_id, message.role, message.content)
    return {"saved": True}


@app.post("/conversation/new")
def start_new_conversation(response: Response):
    """Start a separate conversation while retaining the old JSON record."""
    record = session_manager.create_session()
    conversation_manager.ensure_conversation(record.session_id, record.conversation_id)
    session_manager.set_session_cookie(response, record.session_id)
    return {"created": True, "message": "New conversation ready"}

@app.post("/login")
def login(request: LoginRequest, raw_request: Request, response: Response):
    customers = load_data("customers.json") or []
    for customer in customers:
        if customer["customer_id"].upper() == request.customer_id.upper() and customer["pin"] == request.pin:
            get_browser_session(raw_request, response)
            cust_session = get_session(f"cust_{customer['customer_id'].upper()}")
            cust_session["otp_verified"] = False
            cust_session["pending_action"] = None
            cust_session["pending_transfer"] = None
            return {
                "status": "success",
                "customer": {
                    "customer_id": customer["customer_id"],
                    "name": customer["name"],
                    "account_number": customer["account_number"],
                    "account_type": customer["account_type"],
                    "balance": customer["balance"]
                }
            }
    raise HTTPException(status_code=401, detail="Invalid customer ID or PIN")

@app.post("/chat")
def chat(chat_request: ChatRequest, request: Request, response: Response):
    user_input = chat_request.text.strip()
    is_auth = chat_request.customer_id is not None
    browser_session, _ = get_browser_session(request, response)
    session_id = f"cust_{chat_request.customer_id.upper()}" if chat_request.customer_id else browser_session.session_id
    session = get_session(session_id)
    
    # Detect language (Kannada vs English)
    language = detect_language(user_input)

    # Check if this input is directly an OTP for a pending transfer or personal action
    pending_transfer = session.get("pending_transfer")
    pending_action = session.get("pending_action")
    clean_digits = "".join(filter(str.isdigit, user_input))
    if (pending_transfer or pending_action) and (clean_digits == "123456" or "123456" in user_input):
        target_intent = "fund_transfer" if pending_transfer else (pending_action.get("intent") or "balance_enquiry")
        data = handle_intent(
            intent=target_intent,
            entities={},
            customer_id=chat_request.customer_id,
            is_auth=is_auth,
            session_id=session_id,
            raw_text=user_input
        )
        resolved_intent = data.get("intent", target_intent)
        response_text = generate_natural_response(resolved_intent, data, language)
        conversation_manager.append_message(browser_session.conversation_id, "user", user_input)
        conversation_manager.append_message(
            browser_session.conversation_id,
            "assistant",
            response_text,
            private_response=resolved_intent in {
                "balance_enquiry", "transaction_history", "account_details",
                "spending_analysis", "fund_transfer",
            },
        )
        return {
            "response": response_text,
            "intent": resolved_intent,
            "data": data,
            "language": language
        }

    # 1. Detect Intent and Entities using Gemini / resilient fallback
    gemini_data = get_intent_and_entities(user_input, is_auth)
    intent = gemini_data.get("intent", "unknown")
    entities = gemini_data.get("entities", {})

    # 2. Get Data via backend functions
    data = handle_intent(
        intent=intent,
        entities=entities,
        customer_id=chat_request.customer_id,
        is_auth=is_auth,
        session_id=session_id,
        raw_text=user_input
    )

    # 3. Generate natural response
    resolved_intent = data.get("intent", intent)
    response_text = generate_natural_response(resolved_intent, data, language)

    # Update session conversation history
    session["history"].append({"user": user_input, "bot": response_text})
    conversation_manager.append_message(browser_session.conversation_id, "user", user_input)
    conversation_manager.append_message(
        browser_session.conversation_id,
        "assistant",
        response_text,
        private_response=resolved_intent in {
            "balance_enquiry", "transaction_history", "account_details",
            "spending_analysis", "fund_transfer",
        },
    )

    return {
        "response": response_text,
        "intent": resolved_intent,
        "data": data,
        "language": language
    }

@app.get("/customer/{customer_id}/balance")
def get_customer_balance(customer_id: str):
    balance = get_balance(customer_id)
    if balance is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"customer_id": customer_id, "balance": balance}

@app.get("/customer/{customer_id}/transactions")
def get_customer_transactions(customer_id: str):
    txns = get_transactions(customer_id)
    return {"customer_id": customer_id, "transactions": txns}

@app.get("/customer/{customer_id}/account")
def get_customer_account(customer_id: str):
    account = get_account_details(customer_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"account": account}

@app.get("/customer/{customer_id}/loan")
def get_customer_loans(customer_id: str):
    return {"customer_id": customer_id, "loans": get_loan_information(customer_id)}

@app.post("/emi")
def get_emi(request: EMIRequest):
    emi = calculate_emi(request.principal, request.interest_rate, request.tenure_months)
    return emi

@app.get("/interest-rates")
def get_rates():
    return {"interest_rates": get_interest_rates()}

@app.get("/customer/{customer_id}/insights")
def get_customer_insights(customer_id: str):
    insights = analyze_spending(customer_id)
    return insights

@app.post("/transfer/initiate")
def initiate_transfer(request: TransferInitiateRequest):
    bal = get_balance(request.customer_id)
    if bal is None:
        raise HTTPException(status_code=404, detail="Sender not found")
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid transfer amount")
    if bal < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    return {
        "status": "otp_sent",
        "demo_otp": "123456",
        "amount": request.amount,
        "recipient": request.recipient,
        "message": "A verification OTP has been sent. Demo OTP: 123456"
    }

@app.post("/transfer/verify")
def verify_transfer(request: TransferVerifyRequest):
    if request.otp.strip() != "123456":
        raise HTTPException(status_code=400, detail="Invalid OTP. Please enter demo OTP: 123456")

    result = transfer_money(request.customer_id, request.recipient, request.amount)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transfer failed"))

    return result

# Serve frontend directly for seamless hackathon demo
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend_root(request: Request):
        page = FileResponse(os.path.join(frontend_dir, "index.html"))
        get_browser_session(request, page)
        return page

    @app.get("/style.css")
    def serve_css():
        return FileResponse(os.path.join(frontend_dir, "style.css"))

    @app.get("/script.js")
    def serve_js():
        return FileResponse(os.path.join(frontend_dir, "script.js"))

    @app.get("/translations.js")
    def serve_translations():
        return FileResponse(os.path.join(frontend_dir, "translations.js"))

    @app.get("/{filename:path}")
    def serve_frontend_file(filename: str):
        file_path = os.path.join(frontend_dir, filename)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        raise HTTPException(status_code=404, detail="File not found")

