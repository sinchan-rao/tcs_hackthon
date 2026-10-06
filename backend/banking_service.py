import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_data(filename: str):
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_data(filename: str, data):
    file_path = os.path.join(DATA_DIR, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_customer(customer_id: str):
    customers = load_data("customers.json") or []
    for customer in customers:
        if customer["customer_id"].upper() == customer_id.upper():
            return customer
    return None

def get_balance(customer_id: str):
    customer = get_customer(customer_id)
    if customer:
        return customer.get("balance")
    return None

def get_transactions(customer_id: str):
    transactions_data = load_data("transactions.json") or []
    for item in transactions_data:
        if item["customer_id"].upper() == customer_id.upper():
            # Return sorted by date descending if possible
            txns = item.get("transactions", [])
            return sorted(txns, key=lambda x: x.get("date", ""), reverse=True)
    return []

def get_account_details(customer_id: str):
    customer = get_customer(customer_id)
    if customer:
        return {
            "customer_id": customer.get("customer_id"),
            "name": customer.get("name"),
            "account_number": customer.get("account_number"),
            "account_type": customer.get("account_type"),
            "mobile": customer.get("mobile"),
            "balance": customer.get("balance")
        }
    return None

def get_loan_information(customer_id: str):
    loans_data = load_data("loans.json") or []
    for item in loans_data:
        if item["customer_id"].upper() == customer_id.upper():
            return item.get("loans", [])
    return []

def calculate_emi(principal: float, interest_rate: float, tenure_months: int):
    """
    Calculate EMI using standard banking formula:
    EMI = P * r * (1 + r)^n / ((1 + r)^n - 1)
    where r = (annual_rate / 12) / 100
    """
    if principal <= 0 or interest_rate <= 0 or tenure_months <= 0:
        return 0.0
    
    r = (interest_rate / 12) / 100
    emi = principal * r * ((1 + r) ** tenure_months) / (((1 + r) ** tenure_months) - 1)
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    
    return {
        "monthly_emi": round(emi, 2),
        "total_interest": round(total_interest, 2),
        "total_payment": round(total_payment, 2),
        "principal": principal,
        "interest_rate": interest_rate,
        "tenure_months": tenure_months
    }

def get_interest_rates():
    banking_info = load_data("banking_info.json") or {}
    return banking_info.get("interest_rates", {})

def get_faqs():
    banking_info = load_data("banking_info.json") or {}
    return banking_info.get("faqs", [])

def analyze_spending(customer_id: str):
    """
    Analyzes customer spending:
    - Total monthly spending
    - Category-wise spending
    - Largest category
    - Unusual/high-value transactions
    - Simple savings suggestions
    """
    txns = get_transactions(customer_id)
    if not txns:
        return {
            "total_spending": 0,
            "categories": {},
            "largest_category": "None",
            "unusual_transactions": [],
            "monthly_spending": 0,
            "suggestion": "No transactions recorded yet to generate spending insights."
        }

    total_debit = 0
    categories = {}
    debit_txns = []

    for t in txns:
        if t.get("type") == "debit":
            amt = float(t.get("amount", 0))
            total_debit += amt
            cat = t.get("category", "Other")
            categories[cat] = round(categories.get(cat, 0) + amt, 2)
            debit_txns.append(t)

    largest_cat = max(categories, key=categories.get) if categories else "None"
    largest_cat_amount = categories.get(largest_cat, 0)

    # Detect high-value/unusual transactions (e.g. >= 3000 or top 2 highest)
    sorted_debits = sorted(debit_txns, key=lambda x: x.get("amount", 0), reverse=True)
    unusual_txns = [t for t in sorted_debits if t.get("amount", 0) >= 3000][:3]

    # Generate rule-based suggestion for fallback or structured insight
    if largest_cat.lower() == "food":
        suggestion = f"Your largest spending category is {largest_cat} (₹{largest_cat_amount:,.2f}). Reviewing dining out and online deliveries could help you save ₹1,000–₹2,000 monthly."
    elif largest_cat.lower() == "shopping":
        suggestion = f"Your largest spending category is {largest_cat} (₹{largest_cat_amount:,.2f}). Setting a monthly shopping allowance could increase your monthly savings."
    elif largest_cat.lower() == "travel":
        suggestion = f"Your largest spending category is {largest_cat} (₹{largest_cat_amount:,.2f}). Opting for monthly transit passes could optimize your travel budget."
    elif largest_cat.lower() == "bills":
        suggestion = f"Your largest spending category is {largest_cat} (₹{largest_cat_amount:,.2f}). Reviewing unused subscriptions or optimizing utility plans could trim recurring costs."
    else:
        suggestion = f"Your highest expense category is {largest_cat}. Tracking smaller incidental expenses will boost your overall savings."

    return {
        "customer_id": customer_id,
        "monthly_spending": round(total_debit, 2),
        "total_spending": round(total_debit, 2),
        "categories": categories,
        "largest_category": largest_cat,
        "largest_category_amount": largest_cat_amount,
        "unusual_transactions": unusual_txns,
        "suggestion": suggestion
    }

def transfer_money(customer_id: str, recipient: str, amount: float):
    """
    Executes simulated transfer after OTP verification:
    - Validates sender & balance
    - Debits sender
    - Credits recipient if they exist in customer database
    - Appends transactions
    - Saves updated data to customers.json and transactions.json
    """
    amount = float(amount)
    if amount <= 0:
        return {"success": False, "error": "Transfer amount must be greater than zero."}

    customers = load_data("customers.json") or []
    sender = None
    recipient_customer = None

    for c in customers:
        if c["customer_id"].upper() == customer_id.upper():
            sender = c
        # Check recipient by name or customer_id
        if recipient.strip().lower() in c["name"].lower() or recipient.strip().upper() == c["customer_id"].upper():
            if c["customer_id"].upper() != customer_id.upper():
                recipient_customer = c

    if not sender:
        return {"success": False, "error": "Sender account not found."}

    if sender["balance"] < amount:
        return {
            "success": False,
            "error": f"Insufficient balance. Available: ₹{sender['balance']:,.2f}, Requested: ₹{amount:,.2f}"
        }

    # Debit sender
    sender["balance"] = round(sender["balance"] - amount, 2)

    # Credit recipient if found
    if recipient_customer:
        recipient_customer["balance"] = round(recipient_customer["balance"] + amount, 2)

    # Save customers.json
    save_data("customers.json", customers)

    # Update transactions.json
    transactions_data = load_data("transactions.json") or []
    now_str = datetime.now().strftime("%Y-%m-%d")
    txn_id_debit = f"TXN{int(datetime.now().timestamp()) % 100000:05d}"
    recipient_display_name = recipient_customer["name"] if recipient_customer else recipient

    # Find or create sender transactions list
    sender_found = False
    for item in transactions_data:
        if item["customer_id"].upper() == customer_id.upper():
            sender_found = True
            item["transactions"].insert(0, {
                "id": txn_id_debit,
                "date": now_str,
                "description": f"Transfer to {recipient_display_name}",
                "category": "Transfer",
                "amount": amount,
                "type": "debit"
            })
            break

    if not sender_found:
        transactions_data.append({
            "customer_id": customer_id,
            "transactions": [{
                "id": txn_id_debit,
                "date": now_str,
                "description": f"Transfer to {recipient_display_name}",
                "category": "Transfer",
                "amount": amount,
                "type": "debit"
            }]
        })

    # If recipient customer is local, add credit entry
    if recipient_customer:
        txn_id_credit = f"TXN{(int(datetime.now().timestamp()) + 1) % 100000:05d}"
        recip_found = False
        for item in transactions_data:
            if item["customer_id"].upper() == recipient_customer["customer_id"].upper():
                recip_found = True
                item["transactions"].insert(0, {
                    "id": txn_id_credit,
                    "date": now_str,
                    "description": f"Transfer from {sender['name']}",
                    "category": "Transfer",
                    "amount": amount,
                    "type": "credit"
                })
                break
        if not recip_found:
            transactions_data.append({
                "customer_id": recipient_customer["customer_id"],
                "transactions": [{
                    "id": txn_id_credit,
                    "date": now_str,
                    "description": f"Transfer from {sender['name']}",
                    "category": "Transfer",
                    "amount": amount,
                    "type": "credit"
                }]
            })

    save_data("transactions.json", transactions_data)

    return {
        "success": True,
        "transaction_id": txn_id_debit,
        "amount": amount,
        "recipient": recipient_display_name,
        "remaining_balance": sender["balance"],
        "date": now_str,
        "message": f"Transfer successful. ₹{amount:,.2f} has been transferred to {recipient_display_name}. Remaining balance: ₹{sender['balance']:,.2f}"
    }
