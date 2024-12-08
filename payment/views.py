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
    worker_id = request.session.get("user_id")
    if not worker_id:
        return redirect("login")

    accepted_job = request.session.pop('accepted_job', None)

    with connection.cursor() as cursor:
        # Fetch accepted jobs for the logged-in worker
        cursor.execute("""
            SELECT tso.Id, ssc.SubCategoryName, tso.OrderDate, tso.ServiceDate, os.Status, tos.date
            FROM TR_SERVICE_ORDER tso
            JOIN SERVICE_SUBCATEGORY ssc ON tso.ServiceSubCategoryId = ssc.Id
            JOIN TR_ORDER_STATUS tos ON tso.Id = tos.ServiceTrId
            JOIN ORDER_STATUS os ON tos.StatusId = os.Id
            WHERE tso.WorkerId = %s
            ORDER BY tos.date DESC
        """, [worker_id])
        jobs = cursor.fetchall()

    # Add the accepted job if available
    jobs_data = [
        {
            "id": job[0],
            "subcategory_name": job[1],
            "order_date": job[2],
            "service_date": job[3],
            "status": job[4],
            "status_change_date": job[5],
        }
        for job in jobs
    ]

    if accepted_job:
        jobs_data.insert(0, accepted_job)

    context = {
        "jobs": jobs_data
    }
    return render(request, 'ServiceJob_Status.html', context)




def ServiceJob(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        # Handle accepting a service job
        order_id = request.POST.get("order_id")
        if not order_id:
            messages.error(request, "Invalid order ID.")
            return redirect("servicejob")

        with connection.cursor() as cursor:
            try:
                # Update the worker ID and status of the selected order
                cursor.execute("""
                    UPDATE TR_SERVICE_ORDER
                    SET WorkerId = %s
                    WHERE Id = %s AND Id NOT IN (
                        SELECT ServiceTrId FROM TR_ORDER_STATUS WHERE StatusId IN (
                            SELECT Id FROM ORDER_STATUS WHERE Status = 'Waiting for Worker to Depart'
                        )
                    )
                """, [user_id, order_id])

                if cursor.rowcount == 0:
                    messages.error(request, "Failed to accept the job. It might already be taken.")
                    return redirect("servicejob")

                # Insert the new status into TR_ORDER_STATUS
                cursor.execute("""
                    INSERT INTO TR_ORDER_STATUS (ServiceTrId, StatusId, date)
                    VALUES (
                        %s,
                        (SELECT Id FROM ORDER_STATUS WHERE Status = 'Waiting for Worker to Depart'),
                        NOW()
                    )
                """, [order_id])

                # Fetch job details for immediate display in ServiceJob_Status
                cursor.execute("""
                    SELECT tso.Id, ssc.SubCategoryName, tso.OrderDate, tso.ServiceDate, 
                           (SELECT Status FROM ORDER_STATUS WHERE Id = 
                            (SELECT StatusId FROM TR_ORDER_STATUS WHERE ServiceTrId = tso.Id ORDER BY date DESC LIMIT 1)
                           ) AS Status,
                           NOW() AS StatusChangeDate
                    FROM TR_SERVICE_ORDER tso
                    JOIN SERVICE_SUBCATEGORY ssc ON tso.ServiceSubCategoryId = ssc.Id
                    WHERE tso.Id = %s
                """, [order_id])
                accepted_job = cursor.fetchone()

                # Store the accepted job details in the session for immediate display
                request.session['accepted_job'] = {
                    "id": accepted_job[0],
                    "subcategory_name": accepted_job[1],
                    "order_date": accepted_job[2].strftime("%Y-%m-%d"),
                    "service_date": accepted_job[3].strftime("%Y-%m-%d"),
                    "status": accepted_job[4],
                    "status_change_date": accepted_job[5].strftime("%Y-%m-%d %H:%M:%S"),
                }

                messages.success(request, "Successfully accepted the job.")
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")

        return redirect("servicejob_status")

    # Fetch available service jobs for the worker
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                tso.Id AS OrderId,
                ssc.SubCategoryName AS SubCategory,
                tso.OrderDate,
                tso.ServiceDate,
                ss.Session AS Session,
                ss.Price AS TotalPrice,
                os.Status AS OrderStatus
            FROM TR_SERVICE_ORDER tso
            JOIN SERVICE_SUBCATEGORY ssc ON tso.ServiceSubCategoryId = ssc.Id
            JOIN SERVICE_SESSION ss ON ssc.Id = ss.SubCategoryId
            JOIN TR_ORDER_STATUS tos ON tso.Id = tos.ServiceTrId
            JOIN ORDER_STATUS os ON tos.StatusId = os.Id
            WHERE os.Status = 'Looking for Nearby Worker'
            ORDER BY tso.OrderDate DESC
        """)
        service_jobs = cursor.fetchall()

    context = {
        "service_jobs": [
            {
                "id": row[0],
                "sub_category": row[1],
                "order_date": row[2],
                "service_date": row[3],
                "session": row[4],
                "total_price": float(row[5]),
                "status": row[6],
            }
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

