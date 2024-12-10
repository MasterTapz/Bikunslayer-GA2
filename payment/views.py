# views.py
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db import connection
from django.shortcuts import render
from django.db import connection, transaction
from django.http import JsonResponse
from uuid import uuid4
from datetime import datetime
from django.contrib.auth.decorators import login_required


def MyPay(request):
    user_id = request.session.get('user_id')
    # Fetch user's balance, transactions, and unpaid orders
    with connection.cursor() as cursor:
        # Fetch balance and transactions (existing code)
        cursor.execute("SELECT MyPayBalance FROM users WHERE Id = %s", [user_id])
        row = cursor.fetchone()
    balance = row[0] if row else 0

    # Fetch transaction history
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                tm.Date, 
                tm.Nominal, 
                tc.Name AS Category 
            FROM 
                TR_MYPAY tm
            INNER JOIN 
                TR_MYPAY_CATEGORY tc 
            ON 
                tm.CategoryId = tc.Id
            WHERE 
                tm.userid = %s
            ORDER BY 
                tm.Date DESC
        """, [user_id])
        rows = cursor.fetchall()

    transactions = [
        {
            'date': row[0],
            'nominal': row[1],
            'category': row[2],
        }
        for row in rows
    ]
    print(transaction)
        # Fetch unpaid orders
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                o.Id,
                ss.SubcategoryName AS service_name,
                o.Session,
                ssess.Price
            FROM TR_SERVICE_ORDER o
            JOIN SERVICE_SUBCATEGORY ss ON o.serviceSubCategoryId = ss.Id
            JOIN SERVICE_SESSION ssess ON ssess.SubcategoryId = ss.Id AND ssess.Session = o.Session
            JOIN (
                SELECT ts.serviceTrId, os.Status
                FROM TR_ORDER_STATUS ts
                JOIN ORDER_STATUS os ON ts.statusId = os.Id
                WHERE ts.date = (
                    SELECT MAX(date) 
                    FROM TR_ORDER_STATUS 
                    WHERE serviceTrId = ts.serviceTrId
                )
            ) latest_status ON o.Id = latest_status.serviceTrId
            WHERE o.customerId = %s AND latest_status.Status = 'Waiting for Payment'
        """, [user_id])
        unpaid_orders = cursor.fetchall()
    
            # Format unpaid orders
        unpaid_orders_list = []
        for order in unpaid_orders:
            unpaid_orders_list.append({
                'id': order[0],
                'service_name': order[1],
                'session': order[2],
                'price': order[3],
            })
        print(unpaid_orders_list)

    return render(request, 'mypay.html', {
        'balance': balance,
        'transactions': transactions,
        'unpaid_orders': unpaid_orders_list,
    })

def MyPay_Transaction(request):
    if request.method == 'POST':
        try:
            user_id = request.session.get('user_id')  # Replace with dynamic user logic
            transaction_type = request.POST.get('transactionType')

            if not user_id:
                return JsonResponse({'message': 'Invalid user', 'success': False})

            with connection.cursor() as cursor:
                if transaction_type == 'topUp':
                    amount = float(request.POST.get('topUpAmount', 0))
                    if amount > 0:
                        # Update balance
                        cursor.execute("""
                            UPDATE users
                            SET MyPayBalance = MyPayBalance + %s
                            WHERE Id = %s
                        """, [amount, user_id])

                        # Insert transaction record
                        cursor.execute("""
                            INSERT INTO TR_MYPAY (Id, Date, Nominal, CategoryId, userid)
                            VALUES (%s, %s, %s, %s, %s)
                        """, [str(uuid4()), datetime.now(), amount, 
                            '11111111-1111-1111-1111-111111111111', user_id])

                        # Commit the transaction
                        transaction.commit()

                        return JsonResponse({'message': 'Top-Up successful', 'success': True})

                # Service Payment Logic
                elif transaction_type == 'servicePayment':
                    order_id = request.POST.get('orderId')
                    if not order_id:
                        return JsonResponse({'message': 'Order ID not provided', 'success': False})

                    # Fetch the service price from the SERVICE_SESSION table based on the order details
                    cursor.execute("""
                        SELECT ss.Price
                        FROM TR_SERVICE_ORDER so
                        JOIN SERVICE_SESSION ss ON so.serviceSubCategoryId = ss.SubcategoryId AND so.Session = ss.Session
                        WHERE so.Id = %s
                    """, [order_id])

                    row = cursor.fetchone()
                    if not row:
                        return JsonResponse({'message': 'Service order not found', 'success': False})

                    service_price = row[0]
                    if service_price <= 0:
                        return JsonResponse({'message': 'Invalid service price', 'success': False})

                    # Deduct balance if sufficient funds are available
                    cursor.execute("""
                        UPDATE users
                        SET MyPayBalance = MyPayBalance - %s
                        WHERE Id = %s AND MyPayBalance >= %s
                    """, [service_price, user_id, service_price])

                    if cursor.rowcount == 0:
                        return JsonResponse({'message': 'Insufficient balance', 'success': False})

                    # Insert a new status record to indicate the payment has been made
                    cursor.execute("""
                            INSERT INTO TR_ORDER_STATUS (serviceTrId, statusId, date)
                            VALUES (%s, %s, %s)
                        """, [order_id, '5b04762f-1de7-447e-8276-abd63986253e', datetime.now()])

                    # Insert transaction record
                    cursor.execute("""
                        INSERT INTO TR_MYPAY (Id, Date, Nominal, CategoryId, userid)
                        VALUES (%s, %s, %s, %s, %s)
                    """, [
                        str(uuid4()), datetime.now(), -service_price,
                        '22222222-2222-2222-2222-222222222222', user_id
                    ])

                    transaction.commit()

                    return JsonResponse({'message': 'Service payment successful', 'success': True})

                elif transaction_type == 'transfer':
                    recipient_phone = request.POST.get('recipientPhone')
                    amount = float(request.POST.get('transferAmount', 0))
                    if recipient_phone and amount > 0:
                        cursor.execute("SELECT Id FROM users WHERE PhoneNum = %s", [recipient_phone])
                        recipient = cursor.fetchone()
                        if recipient:
                            recipient_id = recipient[0]

                            # Deduct from sender
                            cursor.execute("""
                                UPDATE users
                                SET MyPayBalance = MyPayBalance - %s
                                WHERE Id = %s AND MyPayBalance >= %s
                            """, [amount, user_id, amount])

                            # Credit to recipient
                            cursor.execute("""
                                UPDATE users
                                SET MyPayBalance = MyPayBalance + %s
                                WHERE Id = %s
                            """, [amount, recipient_id])
                            # Insert transaction records
                            cursor.execute("""
                                INSERT INTO TR_MYPAY (Id, Date, Nominal, CategoryId, userid)
                                VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)
                            """, [str(uuid4()), datetime.now(), -amount, 
                                '44444444-4444-4444-4444-444444444444', user_id,
                                str(uuid4()), datetime.now(), amount, 
                                '44444444-4444-4444-4444-444444444444', recipient_id])

                            transaction.commit()

                            return JsonResponse({'message': 'Transfer successful', 'success': True})
                        else:
                            return JsonResponse({'message': 'Recipient not found', 'success': False})

                elif transaction_type == 'withdrawal':
                                bank_name = request.POST.get('bankName')
                                account_number = request.POST.get('bankAccountNumber')
                                amount = float(request.POST.get('withdrawalAmount', 0))
                                if bank_name and account_number and amount > 0:
                                    cursor.execute("""
                                        UPDATE users
                                        SET MyPayBalance = MyPayBalance - %s
                                        WHERE Id = %s AND MyPayBalance >= %s
                                    """, [amount, user_id, amount])

                                    # Insert transaction record
                                    cursor.execute("""
                                        INSERT INTO TR_MYPAY (Id, Date, Nominal, CategoryId, userid)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, [str(uuid4()), datetime.now(), -amount, 
                                        '55555555-5555-5555-5555-555555555555', user_id])

                                    transaction.commit()

                                    return JsonResponse({'message': 'Withdrawal successful', 'success': True})

        except Exception as e:
            transaction.rollback()
            return JsonResponse({'message': f'Error: {e}', 'success': False})

    return JsonResponse({'message': 'Invalid request', 'success': False})

from django.shortcuts import redirect
from django.contrib import messages
from django.db import connection
from datetime import datetime

def accept_order(request, order_id):
    # Ensure the user is logged in as a worker
    worker_id = request.session.get('user_id')
    if not worker_id:
        messages.error(request, "You must be logged in as a worker to accept orders.")
        return redirect('login')  # or another appropriate URL

    # Update the workerId for the selected order and set a new status
    with connection.cursor() as cursor:
        # Check if the order is currently unassigned and has status 'Finding Nearest Worker'
        cursor.execute("""
            SELECT os.Status 
            FROM tr_service_order tso
            JOIN tr_order_status tos ON tso.Id = tos.serviceTrId
            JOIN order_status os ON tos.statusId = os.Id
            WHERE tso.Id = %s 
            AND tos.date = (
                SELECT MAX(date)
                FROM tr_order_status
                WHERE serviceTrId = tso.Id
            )
        """, [order_id])
        result = cursor.fetchone()

        if not result or result[0] != 'Finding Nearest Worker':
            messages.error(request, "This order cannot be accepted at this stage.")
            return redirect('servicejob')

        # Assign the worker to the order
        cursor.execute("""
            UPDATE tr_service_order
            SET workerId = %s
            WHERE Id = %s
        """, [worker_id, order_id])

        # Insert new status: 'Worker Assigned'
        # First, get the statusId for 'Worker Assigned'
        cursor.execute("SELECT Id FROM order_status WHERE Status = 'Worker Assigned'")
        status_id = cursor.fetchone()
        if status_id:
            cursor.execute("""
                INSERT INTO TR_ORDER_STATUS (serviceTrId, statusId, date)
                VALUES (%s, %s, %s)
            """, [order_id, status_id[0], datetime.now()])

    messages.success(request, "Order accepted successfully!")
    return redirect('servicejob')


def ServiceJob(request):
    worker_id = request.session.get('user_id')  # Assuming the logged-in user is a worker

    # Fetch the worker's registered service categories
    category_query = """
    SELECT wsc.serviceCategoryId, sc.CategoryName
    FROM worker_service_category AS wsc
    LEFT JOIN service_category AS sc ON wsc.serviceCategoryId = sc.Id
    WHERE wsc.workerId = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(category_query, [worker_id])
        worker_service_categories = cursor.fetchall()

    # Fetch all subcategories
    subcategory_query = """
    SELECT subcategory.id::text, subcategory.SubcategoryName, subcategory.ServiceCategoryId::text
    FROM service_subcategory AS subcategory
    """
    with connection.cursor() as cursor:
        cursor.execute(subcategory_query)
        subcategories = cursor.fetchall()

    # Extract selected filters from the request
    selected_category = request.GET.get('category')
    selected_subcategory = request.GET.get('subcategory')

    # Base query to fetch orders
    order_query = """
    SELECT tso.Id, tso.serviceSubCategoryId::text, sc.CategoryName, tso.orderDate, tso.TotalPrice, tso.serviceTime,
        os.Status AS order_status, ss.Session, ss.Price
    FROM tr_service_order AS tso
    LEFT JOIN tr_order_status AS tos ON tso.Id = tos.serviceTrId
    LEFT JOIN order_status AS os ON tos.statusId = os.Id
    LEFT JOIN service_session ss ON tso.serviceSubCategoryId = ss.SubcategoryId AND tso.Session = ss.Session
    LEFT JOIN service_subcategory sub ON ss.SubcategoryId = sub.Id
    LEFT JOIN service_category sc ON sub.ServiceCategoryId = sc.Id
    WHERE (tso.workerId = %s OR tso.workerId IS NULL)
    AND os.Status = 'Finding Nearest Worker'
    AND tos.date = (
        SELECT MAX(date)
        FROM tr_order_status
        WHERE serviceTrId = tso.Id
    )
    """

    # Add category and subcategory filters dynamically
    query_params = [worker_id]
    if selected_category:
        order_query += " AND sub.ServiceCategoryId = %s"
        query_params.append(selected_category)
    if selected_subcategory:
        order_query += " AND ss.SubcategoryId = %s"
        query_params.append(selected_subcategory)

    # Execute the final query
    with connection.cursor() as cursor:
        cursor.execute(order_query, query_params)
        orders = cursor.fetchall()
    print(orders)

    # Filter subcategories based on the selected category
    if selected_category:
        subcategories = [sub for sub in subcategories if sub[2] == selected_category]

    return render(request, 'ServiceJob.html', {
        'orders': orders,
        'subcategories': subcategories,
        'worker_service_categories': worker_service_categories,
        'selected_category': selected_category,
        'selected_subcategory': selected_subcategory,
    })



def ServiceJob_Status(request):
    worker_id = request.session.get('user_id')
    if not worker_id:
        return JsonResponse({'success': False, 'error': 'User not logged in'})

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        order_id = request.POST.get('order_id')
        next_status = request.POST.get('next_status')

        # Update the order status in the database
        with connection.cursor() as cursor:
            # Get the status ID
            cursor.execute("SELECT Id FROM ORDER_STATUS WHERE Status = %s", [next_status])
            status_id = cursor.fetchone()

            if status_id:
                # Insert the new status into TR_ORDER_STATUS
                cursor.execute(
                    "INSERT INTO TR_ORDER_STATUS (serviceTrId, statusId, date) VALUES (%s, %s, %s)",
                    [order_id, status_id[0], datetime.now()]
                )

                # Prepare the next action and status
                status_transitions = {
                    'Waiting for Worker to Depart': ('Arrived at Location', 'Worker Arrived at Location'),
                    'Worker Arrived at Location': ('Providing Service', 'Service in Progress'),
                    'Service in Progress': ('Service Completed', 'Completed'),
                }
                current_status = next_status
                next_action, next_status = status_transitions.get(current_status, (None, None))

                return JsonResponse({
                    'success': True,
                    'current_status': current_status,
                    'next_action': next_action,
                    'next_status': next_status,
                    'order_id': order_id,
                    'update_url': request.build_absolute_uri(),  # URL for form action
                    'csrf_token': request.COOKIES['csrftoken'],  # CSRF token
                })

        return JsonResponse({'success': False, 'error': 'Failed to update status'})


    # Get the status filter from the request
    status_filter = request.GET.get('status_filter')

    # Base query to fetch orders with the most recent status
    query = """
    SELECT 
        ss.SubcategoryName AS service_subcategory,
        u.Name AS user_name,
        o.orderDate,
        o.serviceDate,
        o.Session,
        latest_status.Status AS current_status,
        ssess.Price AS session_price,
        o.Id AS order_id
    FROM TR_SERVICE_ORDER o
    JOIN (
        SELECT ts.serviceTrId, os.Status
        FROM TR_ORDER_STATUS ts
        JOIN ORDER_STATUS os ON ts.statusId = os.Id
        WHERE (ts.serviceTrId, ts.date) IN (
            SELECT serviceTrId, MAX(date)
            FROM TR_ORDER_STATUS
            GROUP BY serviceTrId
        )
    ) latest_status ON o.Id = latest_status.serviceTrId
    JOIN SERVICE_SUBCATEGORY ss ON o.serviceSubCategoryId = ss.Id
    JOIN users u ON o.customerId = u.Id
    LEFT JOIN SERVICE_SESSION ssess ON ss.Id = ssess.SubcategoryId AND o.Session = ssess.Session
    WHERE o.workerId = %s
    """
    
    # Add status filter to the query if provided
    query_params = [worker_id]
    if status_filter:
        query += " AND latest_status.Status = %s"
        query_params.append(status_filter)

    # Add the ORDER BY clause at the end
    query += " ORDER BY o.orderDate DESC"

    # Execute the query
    with connection.cursor() as cursor:
        cursor.execute(query, query_params)
        orders = cursor.fetchall()

    # Define status transitions for handling job status updates
    status_transitions = {
        'Waiting for Worker to Depart': ('Arrived at Location', 'Worker Arrived at Location'),
        'Worker Arrived at Location': ('Providing Service', 'Service in Progress'),
        'Service in Progress': ('Service Completed', 'Completed'),
    }

    # Add the status transition information to the orders
    orders_with_transitions = []
    for order in orders:
        current_status = order[5]
        next_action = None
        next_status = None
        if current_status in status_transitions:
            next_action, next_status = status_transitions[current_status]
        orders_with_transitions.append(order + (next_action, next_status))

    # Handling the POST request for status updates
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        next_status = request.POST.get('next_status')

        # Retrieve the StatusId based on the next_status
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT Id FROM ORDER_STATUS WHERE Status = %s
            """, [next_status])
            status_id = cursor.fetchone()

            if status_id:
                # Insert the new status into TR_ORDER_STATUS
                cursor.execute("""
                    INSERT INTO TR_ORDER_STATUS (serviceTrId, statusId, date)
                    VALUES (%s, %s, %s)
                """, [order_id, status_id[0], datetime.now()])

                messages.success(request, "Order status updated successfully!")
            else:
                messages.error(request, "Invalid status provided.")
            return redirect('servicejob_status')

    return render(request, 'ServiceJob_Status.html', {
        'orders': orders_with_transitions,
        'status_transitions': status_transitions,
        'status_filter': status_filter,
    })
