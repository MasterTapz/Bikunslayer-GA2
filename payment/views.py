# Create your views here.
from django.http import JsonResponse
from django.db import connection
from django.shortcuts import render, redirect
from django.contrib import messages

def MyPay(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    with connection.cursor() as cursor:
        # Fetch user details
        cursor.execute("""
            SELECT PhoneNum, MyPayBalance
            FROM users
            WHERE Id = %s
        """, [user_id])
        user_data = cursor.fetchone()
        
        # Fetch transactions
        cursor.execute("""
            SELECT t.Nominal, t.Date, c.Name AS CategoryName
            FROM tr_mypay t
            JOIN tr_mypay_category c ON t.CategoryId = c.Id
            WHERE t.UserId = %s
            ORDER BY t.Date DESC
        """, [user_id])
        transactions = cursor.fetchall()

    context = {
        "phone_number": user_data[0],
        "balance": user_data[1],
        "transactions": [
            {"nominal": row[0], "date": row[1].strftime("%Y-%m-%d %H:%M:%S"), "category": row[2]}
            for row in transactions
        ],
    }
    return render(request, 'MyPay.html', context)

def MyPay_Transaction(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        # Handle new transaction submission
        try:
            amount = int(request.POST.get("amount"))
            category_id = int(request.POST.get("category_id"))

            with connection.cursor() as cursor:
                # Insert the new transaction
                cursor.execute("""
                    INSERT INTO tr_mypay (UserId, Nominal, Date, CategoryId)
                    VALUES (%s, %s, NOW(), %s)
                """, [user_id, amount, category_id])

                # Update the user's balance
                cursor.execute("""
                    UPDATE users
                    SET MyPayBalance = MyPayBalance + %s
                    WHERE Id = %s
                """, [amount, user_id])

            messages.success(request, "Transaction successfully added.")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
        return redirect("mypay_transaction")

    # Fetch user details and transaction history
    with connection.cursor() as cursor:
        # Fetch the user's phone number and balance
        cursor.execute("""
            SELECT PhoneNum, MyPayBalance FROM users WHERE Id = %s
        """, [user_id])
        user_data = cursor.fetchone()
        phone_number = user_data[0]
        balance = user_data[1]

        # Fetch user's transaction history
        cursor.execute("""
            SELECT t.Nominal, t.Date, c.Name AS CategoryName
            FROM tr_mypay t
            JOIN tr_mypay_category c ON t.CategoryId = c.Id
            WHERE t.UserId = %s
            ORDER BY t.Date DESC
        """, [user_id])
        transactions = cursor.fetchall()

    # Pass transaction history, phone number, and balance to the template
    context = {
        "phone_number": phone_number,
        "balance": balance,
        "transactions": [
            {"nominal": row[0], "date": row[1].strftime("%Y-%m-%d %H:%M:%S"), "category": row[2]}
            for row in transactions
        ],
    }
    return render(request, 'MyPay_Transactions.html', context)




def ServiceJob_Status(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    with connection.cursor() as cursor:
        # Fetch service job status for the user
        cursor.execute("""
            SELECT sj.Id, sj.Status, sj.Description, sj.DateCreated
            FROM service_job sj
            WHERE sj.UserId = %s
            ORDER BY sj.DateCreated DESC
        """, [user_id])
        service_jobs = cursor.fetchall()

    context = {
        "service_jobs": [
            {"id": row[0], "status": row[1], "description": row[2], "date_created": row[3]}
            for row in service_jobs
        ],
    }
    return render(request, 'ServiceJob_Status.html', context)

def ServiceJob(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    with connection.cursor() as cursor:
        # Fetch available service jobs for the user
        cursor.execute("""
            SELECT sj.Id, sj.Description, sj.DateCreated, sj.Status
            FROM service_job sj
            WHERE sj.UserId = %s AND sj.Status = 'Available'
            ORDER BY sj.DateCreated DESC
        """, [user_id])
        service_jobs = cursor.fetchall()

    context = {
        "service_jobs": [
            {"id": row[0], "description": row[1], "date_created": row[2], "status": row[3]}
            for row in service_jobs
        ],
    }
    return render(request, 'ServiceJob.html', context)



# Helper function to execute raw SQL queries and return results as dictionaries
def dict_fetch_all(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Fetch users data
def get_users(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                Id, Name, Sex, PhoneNum, Pwd, DoB, Address, MyPayBalance
            FROM users
        """)
        users = dict_fetch_all(cursor)
    return JsonResponse({'users': users})

# Fetch MyPay transactions data
def get_tr_mypay(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                Id, UserId, Date, Nominal, CategoryId
            FROM TR_MYPAY
        """)
        tr_mypay = dict_fetch_all(cursor)
    return JsonResponse({'tr_mypay': tr_mypay})

# Fetch MyPay categories data
def get_tr_mypay_categories(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                Id, Name
            FROM TR_MYPAY_CATEGORY
        """)
        tr_mypay_categories = dict_fetch_all(cursor)
    return JsonResponse({'tr_mypay_categories': tr_mypay_categories})

def topup(request):
    if request.method == "POST":
        user_id = request.session.get("user_id")
        amount = int(request.POST.get("amount", 0))
        
        if amount <= 0:
            messages.error(request, "Invalid top-up amount.")
            return redirect("mypay_transaction")

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET MyPayBalance = MyPayBalance + %s
                WHERE Id = %s
            """, [amount, user_id])

        messages.success(request, f"Successfully topped up Rp{amount}.")
        return redirect("mypay")

def service_payment(request):
    if request.method == "POST":
        user_id = request.session.get("user_id")
        price = int(request.POST.get("price", 0))

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT MyPayBalance 
                FROM users 
                WHERE Id = %s
            """, [user_id])
            balance = cursor.fetchone()[0]

        if balance < price:
            messages.error(request, "Insufficient balance for service payment.")
            return redirect("mypay_transaction")

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET MyPayBalance = MyPayBalance - %s
                WHERE Id = %s
            """, [price, user_id])

        messages.success(request, f"Service payment of Rp{price} completed.")
        return redirect("mypay")

def transfer(request):
    if request.method == "POST":
        sender_id = request.session.get("user_id")
        recipient_phone = request.POST.get("recipient_phone")
        amount = int(request.POST.get("amount", 0))

        with connection.cursor() as cursor:
            # Verify recipient exists
            cursor.execute("""
                SELECT Id FROM users WHERE PhoneNum = %s
            """, [recipient_phone])
            recipient = cursor.fetchone()

        if not recipient:
            messages.error(request, "Recipient not found.")
            return redirect("mypay_transaction")

        recipient_id = recipient[0]

        # Deduct from sender and add to recipient
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET MyPayBalance = MyPayBalance - %s
                WHERE Id = %s AND MyPayBalance >= %s
            """, [amount, sender_id, amount])

            if cursor.rowcount == 0:
                messages.error(request, "Insufficient balance for transfer.")
                return redirect("mypay_transaction")

            cursor.execute("""
                UPDATE users 
                SET MyPayBalance = MyPayBalance + %s
                WHERE Id = %s
            """, [amount, recipient_id])

        messages.success(request, f"Successfully transferred Rp{amount} to {recipient_phone}.")
        return redirect("mypay")

def withdrawal(request):
    if request.method == "POST":
        user_id = request.session.get("user_id")
        amount = int(request.POST.get("amount", 0))

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT MyPayBalance 
                FROM users 
                WHERE Id = %s
            """, [user_id])
            balance = cursor.fetchone()[0]

        if balance < amount:
            messages.error(request, "Insufficient balance for withdrawal.")
            return redirect("mypay_transaction")

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET MyPayBalance = MyPayBalance - %s
                WHERE Id = %s
            """, [amount, user_id])

        messages.success(request, f"Successfully withdrew Rp{amount}.")
        return redirect("mypay")

