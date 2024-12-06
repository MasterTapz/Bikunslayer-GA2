from django.shortcuts import render
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

@csrf_exempt
def purchase_voucher(request):
    if request.method == 'POST':
        try:
            # Parse the request data
            data = json.loads(request.body)
            voucher_code = data.get('code')
            payment_method = data.get('paymentMethod')

            if not voucher_code or not payment_method:
                return JsonResponse({'success': False, 'message': 'Missing voucher code or payment method'})

            # Example: Replace with actual logged-in user's ID
            user_id = 1  # Get this from session, token, or user context

            # Establish DB connection
            conn = get_db_connection()
            cursor = conn.cursor()

            # Fetch voucher details
            cursor.execute("SELECT discount_price FROM vouchers WHERE code = %s", (voucher_code,))
            voucher = cursor.fetchone()

            if not voucher:
                return JsonResponse({'success': False, 'message': 'Invalid voucher code'})

            voucher_price = voucher[0]

            if payment_method == 'MyPay':
                # Fetch user's balance
                cursor.execute("SELECT mypay_balance FROM users WHERE id = %s", (user_id,))
                user = cursor.fetchone()

                if not user:
                    return JsonResponse({'success': False, 'message': 'User not found'})

                user_balance = user[0]

                if user_balance < voucher_price:
                    return JsonResponse({'success': False, 'message': 'Insufficient balance'})

                # Deduct balance
                cursor.execute(
                    "UPDATE users SET mypay_balance = mypay_balance - %s WHERE id = %s",
                    (voucher_price, user_id)
                )

            # Insert the purchase record
            cursor.execute(
                "INSERT INTO purchases (user_id, voucher_code, payment_method) VALUES (%s, %s, %s)",
                (user_id, voucher_code, payment_method)
            )

            # Commit transaction
            conn.commit()

            return JsonResponse({'success': True, 'message': 'Voucher purchased successfully'})

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'success': False, 'message': 'An error occurred'})
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


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
