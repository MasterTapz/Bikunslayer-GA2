from django.shortcuts import render, redirect
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import psycopg2  

def view_discount(request):
    return render(request, 'discount.html')

def view_testimony(request):
    return render(request, 'testimony.html')

def view_voucher(request):
    return render(request, 'voucher.html')

from django.http import JsonResponse
from django.db import connection

# Helper function to execute raw SQL queries
def execute_query(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return results

# views.py

def get_discounts(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT D.Code, D.Discount, D.MinTrOrder
            FROM DISCOUNT D
        """)
        discounts = dict_fetch_all(cursor)
    return JsonResponse({'discounts': discounts})

def get_vouchers(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT D.Code, D.Discount, D.MinTrOrder, V.NmbDayValid, V.UserQuota, V.Price
            FROM DISCOUNT D
            INNER JOIN VOUCHER V ON D.Code = V.Code
        """)
        vouchers = dict_fetch_all(cursor)
    return JsonResponse({'vouchers': vouchers})

def get_promotions(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT D.Code, D.Discount, D.MinTrOrder, P.OfferEndDate
            FROM DISCOUNT D
            INNER JOIN PROMO P ON D.Code = P.Code
        """)
        promotions = dict_fetch_all(cursor)
    return JsonResponse({'promotions': promotions})

def get_testimonials(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                T.date AS date,
                T.Text AS text,
                T.Rating AS rating,
                U.Name AS username,
                UW.Name AS workername
            FROM TESTIMONI T
            INNER JOIN TR_SERVICE_ORDER S ON T.ServiceTrId = S.Id
            INNER JOIN customer C ON S.customerId = C.Id
            INNER JOIN users U ON C.Id = U.Id
            INNER JOIN worker W ON S.workerId = W.Id
            INNER JOIN users UW ON W.Id = UW.Id
        """)
        testimonials = dict_fetch_all(cursor)
    return JsonResponse({'testimonials': testimonials})
def dict_fetch_all(cursor):
    # Return all rows from a cursor as a dict
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]



def get_db_connection():
    return psycopg2.connect(**DATABASE_CONFIG)  # Change `psycopg2` if using another DB driver

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

@csrf_exempt
def create_testimonial(request):
    if request.method == 'POST':
        try:
            # Parse request data
            data = json.loads(request.body)
            worker_name = data.get('worker')
            rating = data.get('rating')
            comment = data.get('comment')

            # Fetch logged-in user info from the session
            user_id = request.session.get('user_id')
            user_name = request.session.get('user_name')

            # Ensure the user is logged in
            if not user_id or not user_name:
                return JsonResponse({'success': False, 'message': 'You must be logged in to submit a testimonial.'})

            # Validate inputs
            if not worker_name or not rating or not comment:
                return JsonResponse({'success': False, 'message': 'All fields are required.'})

            # Fetch ServiceTrId linked to the worker
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT S.Id
                    FROM TR_SERVICE_ORDER S
                    INNER JOIN worker W ON S.workerId = W.Id
                    INNER JOIN users U ON W.Id = U.Id
                    WHERE U.Name = %s
                    ORDER BY S.serviceDate DESC
                    LIMIT 1
                """, [worker_name])
                service_order = cursor.fetchone()

                if not service_order:
                    return JsonResponse({'success': False, 'message': 'No matching service order found for the worker.'})

                service_tr_id = service_order[0]

                # Check if a testimonial for this ServiceTrId already exists for today
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TESTIMONI
                    WHERE ServiceTrId = %s AND date = CURRENT_DATE
                """, [service_tr_id])
                exists = cursor.fetchone()[0]

                if exists:
                    return JsonResponse({'success': False, 'message': 'A testimonial for this service order already exists today.'})

                # Insert the testimonial into the TESTIMONI table
                cursor.execute("""
                    INSERT INTO TESTIMONI (ServiceTrId, date, Text, Rating)
                    VALUES (%s, CURRENT_DATE, %s, %s)
                """, [service_tr_id, comment, rating])

            return JsonResponse({
                'success': True,
                'message': 'Testimonial created successfully!',
                'username': user_name  # Include logged-in user's name in the response
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


import psycopg2
from datetime import date, timedelta
from django.http import JsonResponse


import psycopg2
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from datetime import date, timedelta
from django.contrib import messages


@csrf_exempt

def purchase_voucher(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        try:
            # Fetch the voucher code from the request
            voucher_code = request.POST.get("voucher_code")
            payment_method = request.POST.get("payment_method")

            with connection.cursor() as cursor:
                # Step 1: Fetch the voucher details
                cursor.execute("""
                    SELECT Price
                    FROM voucher
                    WHERE Code = %s
                """, [voucher_code])
                voucher_data = cursor.fetchone()
                if not voucher_data:
                    messages.error(request, "Voucher does not exist.")
                    return redirect("mypay")

                voucher_price = voucher_data[0]

                # Step 2: Fetch the user's current balance
                cursor.execute("""
                    SELECT MyPayBalance
                    FROM users
                    WHERE Id = %s
                """, [user_id])
                user_data = cursor.fetchone()
                if not user_data:
                    messages.error(request, "User does not exist.")
                    return redirect("mypay")

                user_balance = user_data[0]

                # Step 3: Check if balance is sufficient
                if user_balance < voucher_price:
                    messages.error(request, "Insufficient balance.")
                    return redirect("mypay")

                # Step 4: Deduct the balance
                cursor.execute("""
                    UPDATE users
                    SET MyPayBalance = MyPayBalance - %s
                    WHERE Id = %s
                """, [voucher_price, user_id])

                # Step 5: Insert the voucher purchase transaction
                cursor.execute("""
                    INSERT INTO tr_voucher_payment
                    (Id, PurchasedDate, ExpirationDate, AlreadyUse, CustomerId, VoucherId, PaymentMethodId)
                    VALUES (
                        gen_random_uuid(),
                        NOW(),
                        NOW() + INTERVAL '30 days', -- Assuming a 30-day validity
                        0,
                        %s,
                        %s,
                        (SELECT Id FROM payment_method WHERE Name = %s LIMIT 1)
                    )
                """, [user_id, voucher_code, payment_method])

            messages.success(request, "Voucher purchased successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: {e}")
        return redirect("mypay")

    else:
        messages.error(request, "Invalid request method.")
        return redirect("mypay")

