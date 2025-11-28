import json

# Mapping of original IDs to new usernames
id_map = {
    "A": "user01",
    "R": "user02",
    "K": "user03",
    "I": "user04",
    "E": "user05",
    "G": "user06",
    "C": "user07",
    "L": "user08",
    "D": "user09",
    "P": "user10",
    "N": "user11",
    "J": "user12",
    "user13": "user13",
    "S": "user14"
}

def transform_data():
    with open('data.json', 'r') as f:
        data = json.load(f)
    
    new_data = []
    import random
    
    merchants = {
        "Normal_Transaction": ["Amazon", "Uber", "Walmart", "Starbucks", "Netflix", "Apple Store", "Shell Station"],
        "EMI_Repayment": ["Lumin Bank Loan", "HDFC Auto Loan", "SBI Home Loan"],
        "CC_Min_Payment": ["Credit Card Payment"],
        "CC_Full_Payment": ["Credit Card Payment"],
        "Loan_Repayment": ["Personal Loan Repayment"],
        "Salary_Credit": ["Tech Corp Inc.", "Global Services Ltd", "StartUp Hub"],
        "Large_Purchase": ["Apple Store", "Best Buy", "IKEA", "Tanishq Jewellers"],
        "Cash_Advance": ["ATM Withdrawal"],
        "Credit_Inquiry": ["Bank Inquiry"],
        "New_Account_Opened": ["New Bank Account"]
    }

    for user in data:
        original_id = user.get('user_id')
        if original_id in id_map:
            new_user = user.copy()
            new_user['username'] = id_map[original_id]
            new_user['password'] = id_map[original_id]
            new_user['id'] = int(id_map[original_id].replace('user', ''))
            new_user['name'] = f"User {original_id}"
            new_user['email'] = f"{id_map[original_id]}@example.com"
            
            new_user['income'] = user.get('annual_income')
            # Requirement: "current balance ... based on the estincome/12"
            new_user['debt'] = int(new_user['income'] / 12)
            
            missed = user.get('num_missed_payments_12m', 0)
            new_user['payment_history'] = max(0, 100 - (missed * 10))
            
            # Enhance Transactions
            if 'transactions' in new_user:
                for tx in new_user['transactions']:
                    # Add merchant
                    tx_type = tx.get('type', 'Normal_Transaction')
                    if tx_type in merchants:
                        tx['merchant'] = random.choice(merchants[tx_type])
                    else:
                        tx['merchant'] = "Unknown Merchant"
                    
                    # Ensure amount is int
                    tx['amount'] = int(tx.get('amount', 0))
                    
                    # Add category for frontend icon logic if needed (optional)
                    if 'EMI' in tx_type or 'Repayment' in tx_type:
                        tx['category'] = "Bills & Utilities"
                    elif 'Salary' in tx_type:
                        tx['category'] = "Income"
                    else:
                        tx['category'] = "Shopping"

            new_data.append(new_user)
            
    # Sort by username
    new_data.sort(key=lambda x: x['username'])
    
    with open('backend/user_data.json', 'w') as f:
        json.dump(new_data, f, indent=4)
        
    print(f"Mapped {len(new_data)} users to backend/user_data.json with merchants added.")

if __name__ == "__main__":
    # Create backend directory if it doesn't exist (it should, but just in case)
    import os
    if not os.path.exists('backend'):
        os.makedirs('backend')
    transform_data()
