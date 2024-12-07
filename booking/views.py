from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db import connection
from django.shortcuts import redirect, render
from django.urls import reverse
from datetime import datetime

# Checking Functions

def check_database_connection(request):
    """
    Check the database connection.
    """
    try:
        connection.ensure_connection()
        return HttpResponse("Database is connected!")
    except Exception as e:
        return HttpResponse(f"Database connection failed: {e}")


def check_all_ids(request):
    """
    Retrieve and display all relevant IDs from the database.
    """
    data = {
        'users': fetch_table_ids('users', ['Id', 'Name', 'Sex']),
        'customers': fetch_table_ids('customer', ['Id', 'Level']),
        'workers': fetch_table_ids('worker', ['Id', 'BankName', 'Rate']),
        'service_categories': fetch_table_ids('service_category', ['Id', 'CategoryName']),
        'service_subcategories': fetch_table_ids('service_subcategory', ['Id', 'SubCategoryName', 'Description']),
        'service_sessions': fetch_table_ids('service_session', ['SubCategoryId', 'Session', 'Price']),
        'testimonies': fetch_table_ids('testimoni', ['ServiceTrId', 'date', 'Rating']),
    }
    return JsonResponse(data, safe=False)


def fetch_table_ids(table_name, columns):
    """
    Generic function to fetch specified columns from a table.
    """
    query = f"SELECT {', '.join(columns)} FROM {table_name}"
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


# View Functions
def my_orders(request):
    """
    View to fetch and display all orders of the logged-in customer.
    """
    customer_id = request.session.get("user_id")

    if not customer_id:
        return HttpResponse("Unauthorized", status=401)

    query = """
        SELECT 
            tso.Id AS id,
            tso.OrderDate AS order_date,
            tso.ServiceDate AS service_date,
            tso.ServiceTime AS service_time,
            ss.SubCategoryName AS subcategory,
            tso.Session AS session,
            tso.TotalPrice AS total_price,
            tso.DiscountCode AS discount_code,
            pm.Name AS payment_method,
            u.Name AS worker,
            os.Status AS status
        FROM TR_SERVICE_ORDER tso
        LEFT JOIN SERVICE_SUBCATEGORY ss ON tso.ServiceSubCategoryId = ss.Id
        LEFT JOIN PAYMENT_METHOD pm ON tso.PaymentMethodId = pm.Id
        LEFT JOIN WORKER w ON tso.WorkerId = w.Id
        LEFT JOIN USERS u ON w.Id = u.Id
        LEFT JOIN TR_ORDER_STATUS tos ON tso.Id = tos.ServiceTrId
        LEFT JOIN ORDER_STATUS os ON tos.StatusId = os.Id
        WHERE tso.CustomerId = %s
        ORDER BY tso.OrderDate DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [customer_id])
        orders = [
            dict(zip([col[0] for col in cursor.description], row))
            for row in cursor.fetchall()
        ]

    return render(request, 'MyOrder.html', {'orders': orders})


from decimal import Decimal

from datetime import date
from decimal import Decimal

def my_orders(request):
    """
    View to fetch and display all orders of the logged-in customer.
    """
    customer_id = request.session.get("user_id")

    if not customer_id:
        return HttpResponse("Unauthorized", status=401)

    query = """
        SELECT 
            tso.Id AS id,
            tso.OrderDate AS order_date,
            tso.ServiceDate AS service_date,
            tso.ServiceTime AS service_time,
            ss.SubCategoryName AS subcategory,
            tso.Session AS session,
            tso.TotalPrice AS total_price,
            tso.DiscountCode AS discount_code,
            pm.Name AS payment_method,
            u.Name AS worker,
            os.Status AS status
        FROM TR_SERVICE_ORDER tso
        LEFT JOIN SERVICE_SUBCATEGORY ss ON tso.ServiceSubCategoryId = ss.Id
        LEFT JOIN PAYMENT_METHOD pm ON tso.PaymentMethodId = pm.Id
        LEFT JOIN WORKER w ON tso.WorkerId = w.Id
        LEFT JOIN USERS u ON w.Id = u.Id
        LEFT JOIN TR_ORDER_STATUS tos ON tso.Id = tos.ServiceTrId
        LEFT JOIN ORDER_STATUS os ON tos.StatusId = os.Id
        WHERE tso.CustomerId = %s
        ORDER BY tso.OrderDate DESC
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [customer_id])
        orders = [
            dict(zip([col[0] for col in cursor.description], row))
            for row in cursor.fetchall()
        ]

    return render(request, 'MyOrder.html', {'orders': orders})
from django.contrib import messages

def book_service(request, subcategory_id, session):
    """
    Handle booking a service session.
    """
    if request.method == "POST":
        try:
            # Retrieve values from the POST request
            price = Decimal(request.POST.get("price"))  # Convert price to Decimal
            service_date = request.POST.get("serviceDate")
            service_time = request.POST.get("serviceTime")
            worker_id = request.POST.get("workerId")
            discount_code = request.POST.get("discountCode") or None
            promo_code = request.POST.get("promoCode") or None
            payment_method_id = request.POST.get("paymentMethodId")
            customer_id = request.session.get("user_id")

            # Apply discount code if provided
            if discount_code:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT Discount
                        FROM DISCOUNT
                        WHERE Code = %s
                    """, [discount_code])
                    discount_data = cursor.fetchone()
                    if discount_data:
                        discount_percentage = Decimal(discount_data[0])  # Ensure discount is Decimal
                        # Apply discount to price
                        price -= price * (discount_percentage / Decimal(100))

            # Apply promo code if provided
            if promo_code:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT d.Discount, d.MinTrOrder, p.OfferEndDate
                        FROM PROMO p
                        INNER JOIN DISCOUNT d ON p.Code = d.Code
                        WHERE p.Code = %s
                    """, [promo_code])
                    promo_data = cursor.fetchone()
                    if promo_data:
                        promo_discount, min_order, offer_end_date = list(map(Decimal, promo_data[:2])) + [promo_data[2]]
                        
                        # Validate promo code expiration
                        if offer_end_date < datetime.now().date():
                            return JsonResponse({'error': 'The promo code has expired.'}, status=400)

                        # Validate minimum transaction order
                        if price < min_order:
                            return JsonResponse({'error': 'Order does not meet the minimum requirement for this promo code.'}, status=400)

                        # Apply promo discount
                        price = price - (price * (promo_discount / Decimal(100)))


            # Insert into TR_SERVICE_ORDER
            query = """
                INSERT INTO TR_SERVICE_ORDER (
                    Id, OrderDate, ServiceDate, ServiceTime, CustomerId,
                    WorkerId, ServiceSubCategoryId, Session, TotalPrice,
                    DiscountCode, PaymentMethodId
                ) VALUES (
                    gen_random_uuid(), CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """
            with connection.cursor() as cursor:
                cursor.execute(query, [
                    service_date, service_time, customer_id, worker_id,
                    subcategory_id, session, price, discount_code, payment_method_id
                ])

            messages.success(request, 'Service booked successfully!')
            return redirect('subcategory_detail', subcategory_id=subcategory_id)

        except Exception as e:
            return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def view_subcategory_detail(request, subcategory_id):
    subcategory = fetch_subcategory_by_id(subcategory_id)
    sessions = fetch_service_sessions(subcategory_id)
    workers = fetch_workers(subcategory_id)
    testimonials = fetch_testimonials_by_subcategory(subcategory_id)
    user_id = request.session.get("user_id")
    user_vouchers = get_user_vouchers(user_id) if user_id else []
    promotions = get_promotions(request)

    print("Promotions Data:", promotions)

    # Fetch available payment methods
    payment_methods_query = "SELECT Id, Name FROM PAYMENT_METHOD"
    with connection.cursor() as cursor:
        cursor.execute(payment_methods_query)
        payment_methods = [
            {"id": row[0], "name": row[1]} for row in cursor.fetchall()
        ]

    context = {
        'subcategory': subcategory,
        'sessions': sessions,
        'workers': workers,
        'testimonials': testimonials,
        'payment_methods': payment_methods,
        "user_vouchers": user_vouchers,
        'promotions': promotions,
    }
    return render(request, 'subcategory_detail.html', context)


def get_promotions(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT D.Code, D.Discount, D.MinTrOrder, P.OfferEndDate
            FROM DISCOUNT D
            INNER JOIN PROMO P ON D.Code = P.Code
            WHERE P.OfferEndDate >= CURRENT_DATE
        """)
        promotions = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
    return promotions



def view_subcategory_detail_worker(request, subcategory_id, worker_id):
    """
    View for displaying subcategory details and worker status.
    """
    # Fetch subcategory details
    subcategory_query = "SELECT * FROM service_subcategory WHERE Id = %s"
    with connection.cursor() as cursor:
        cursor.execute(subcategory_query, [subcategory_id])
        subcategory = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

    # Fetch worker details, including name from users
    worker_query = """
        SELECT w.Id, w.BankName, w.Rate, u.Name AS WorkerName
        FROM worker w
        JOIN users u ON w.Id = u.Id
        WHERE w.Id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(worker_query, [worker_id])
        worker = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))

    # Check if the worker is joined in this subcategory
    is_joined_query = """
        SELECT EXISTS (
            SELECT 1
            FROM worker_service_category wsc
            JOIN service_subcategory ss ON ss.ServiceCategoryId = wsc.ServiceCategoryId
            WHERE wsc.WorkerId = %s AND ss.Id = %s
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(is_joined_query, [worker_id, subcategory_id])
        is_joined = cursor.fetchone()[0]

    # Fetch service sessions for the subcategory
    sessions_query = "SELECT * FROM service_session WHERE SubCategoryId = %s"
    with connection.cursor() as cursor:
        cursor.execute(sessions_query, [subcategory_id])
        sessions = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

    # Fetch other workers doing the same job
    other_workers = fetch_other_workers(subcategory_id, worker_id)

    context = {
        'subcategory': subcategory,
        'worker': worker,
        'is_joined': is_joined,
        'sessions': sessions,
        'other_workers': other_workers,  # Added
    }
    return render(request, 'subcategory_detail_worker.html', context)




def view_categories(request):
    """
    View for displaying categories and their subcategories.
    """
    categories = fetch_service_categories()
    subcategories = fetch_service_subcategories()

    for category in categories:
        category['subcategories'] = [
            sub for sub in subcategories if sub['servicecategoryid'] == category['id']
        ]

    return render(request, 'categories.html', {'categories': categories})



# Fetching Functions

def check_worker_join_status(worker_id, subcategory_id):
    query = """
        SELECT EXISTS(
            SELECT 1
            FROM worker_service_category wsc
            JOIN service_subcategory ss ON ss.ServiceCategoryId = wsc.ServiceCategoryId
            WHERE wsc.WorkerId = %s AND ss.Id = %s
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [worker_id, subcategory_id])
        return cursor.fetchone()[0]


def fetch_worker_by_id(worker_id):
    query = "SELECT * FROM worker WHERE Id = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, [worker_id])
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


from django.shortcuts import redirect
from django.http import HttpResponse

def join_subcategory(request, subcategory_id, worker_id):
    """
    Adds the worker to the subcategory by inserting into the worker_service_category table.
    """
    if request.method == "POST":
        # Query to find the service category ID from the subcategory ID
        get_service_category_id_query = """
            SELECT ServiceCategoryId FROM service_subcategory WHERE Id = %s
        """
        with connection.cursor() as cursor:
            cursor.execute(get_service_category_id_query, [subcategory_id])
            service_category_id = cursor.fetchone()

            if service_category_id:
                # Insert into worker_service_category
                insert_query = """
                    INSERT INTO worker_service_category (WorkerId, ServiceCategoryId)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                """
                cursor.execute(insert_query, [worker_id, service_category_id[0]])
                return redirect('subcategory_detail_worker', subcategory_id=subcategory_id, worker_id=worker_id)
            else:
                return HttpResponse("Invalid subcategory ID", status=400)
    return HttpResponse("Invalid request method", status=405)



def leave_subcategory(request, subcategory_id, worker_id):
    """
    Removes the worker from the subcategory.
    """
    query = """
        DELETE FROM worker_service_category
        WHERE WorkerId = %s AND ServiceCategoryId IN (
            SELECT ServiceCategoryId
            FROM service_subcategory
            WHERE Id = %s
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [worker_id, subcategory_id])

    return HttpResponseRedirect(reverse('subcategory_detail_worker', args=[subcategory_id, worker_id]))



def fetch_service_categories():
    """
    Fetch all service categories.
    """
    query = "SELECT * FROM service_category"
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def fetch_service_subcategories():
    """
    Fetch all service subcategories.
    """
    query = "SELECT * FROM service_subcategory"
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def fetch_subcategory_by_id(subcategory_id):
    """
    Fetch a specific subcategory by ID.
    """
    query = "SELECT * FROM service_subcategory WHERE Id = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, [subcategory_id])
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
    return dict(zip(columns, row)) if row else None


def fetch_service_sessions(subcategory_id):
    """
    Fetch service sessions for a specific subcategory.
    """
    query = "SELECT * FROM service_session WHERE SubCategoryId = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, [subcategory_id])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def fetch_workers(subcategory_id):
    """
    Fetch workers related to a specific subcategory, including their names from the users table.
    """
    query = """
        SELECT DISTINCT w.Id, w.BankName, w.Rate, u.Name AS WorkerName
        FROM worker w
        JOIN worker_service_category wsc ON w.Id = wsc.WorkerId
        JOIN service_category sc ON wsc.ServiceCategoryId = sc.Id
        JOIN service_subcategory ss ON sc.Id = ss.ServiceCategoryId
        JOIN users u ON w.Id = u.Id
        WHERE ss.Id = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [subcategory_id])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]




def fetch_testimoni(subcategory_id):
    """
    Fetch testimonials for a specific subcategory.
    """
    query = """
        SELECT t.ServiceTrId, t.Text AS TestimonialText, t.Rating, w.BankName AS WorkerName
        FROM testimoni t
        JOIN TR_SERVICE_ORDER tso ON t.ServiceTrId = tso.Id
        JOIN worker w ON tso.WorkerId = w.Id
        WHERE tso.ServiceSubCategoryId = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [subcategory_id])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]

def fetch_other_workers(subcategory_id, current_worker_id):
    query = """
        SELECT DISTINCT u.Name AS workername, w.BankName, w.Rate
        FROM worker w
        JOIN users u ON w.Id = u.Id
        JOIN worker_service_category wsc ON w.Id = wsc.WorkerId
        JOIN service_subcategory ss ON wsc.ServiceCategoryId = ss.ServiceCategoryId
        WHERE ss.Id = %s AND w.Id != %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [subcategory_id, current_worker_id])
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]


def fetch_testimonials(subcategory_id):
    """
    Fetch testimonials for workers associated with a specific subcategory.
    """
    testimonials_query = """
        SELECT t.username, t.comment, t.rating, u.Name AS workername
        FROM testimonial t
        JOIN users u ON t.worker_id = u.Id
        WHERE t.worker_id IN (
            SELECT wsc.WorkerId
            FROM worker_service_category wsc
            JOIN service_subcategory ss ON ss.ServiceCategoryId = wsc.ServiceCategoryId
            WHERE ss.Id = %s
        )
    """
    with connection.cursor() as cursor:
        cursor.execute(testimonials_query, [subcategory_id])
        testimonials = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
    return testimonials

def fetch_testimonials_by_subcategory(subcategory_id):
    """
    Fetch testimonials for workers associated with a specific subcategory,
    including the creator (customer) of the testimonials, sorted by rating (highest to lowest).
    """
    testimonials_query = """
        SELECT 
            t.date AS testimony_date,
            t.text AS comment,
            t.rating AS testimony_rating,
            uc.name AS customer_name,  -- Fetch customer (testimonial creator) name
            uw.name AS worker_name,    -- Fetch worker name
            tso.servicesubcategoryid AS subcategory_id,
            w.id AS worker_id,
            w.rate AS worker_rating
        FROM testimoni t
        LEFT JOIN tr_service_order tso ON t.servicetrid = tso.id
        LEFT JOIN worker w ON tso.workerid = w.id
        LEFT JOIN users uw ON w.id = uw.id -- Join to get worker name
        LEFT JOIN customer c ON tso.customerid = c.id
        LEFT JOIN users uc ON c.id = uc.id -- Join to get customer name
        WHERE tso.servicesubcategoryid = %s OR t.servicetrid = '00000000-0000-0000-0000-000000000000'
        ORDER BY t.rating DESC;
    """
    with connection.cursor() as cursor:
        cursor.execute(testimonials_query, [subcategory_id])
        testimonials = [
            dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()
        ]
    return testimonials



from django.db import connection

def get_user_vouchers(user_id):
    """
    Fetches all vouchers purchased by a user.

    Args:
        user_id (str): The UUID of the user.

    Returns:
        list: A list of dictionaries containing voucher details.
    """
    query = """
        SELECT 
            tvp.Id AS transaction_id,
            tvp.PurchasedDate AS purchased_date,
            tvp.ExpirationDate AS expiration_date,
            tvp.AlreadyUse AS already_used,
            v.Code AS voucher_code,
            v.NmbDayValid AS valid_days,
            v.UserQuota AS user_quota,
            v.Price AS price,
            d.Discount AS discount_percentage,
            d.MinTrOrder AS minimum_transaction_order
        FROM 
            TR_VOUCHER_PAYMENT tvp
        INNER JOIN 
            VOUCHER v ON tvp.VoucherId = v.Code
        INNER JOIN 
            DISCOUNT d ON v.Code = d.Code
        WHERE 
            tvp.CustomerId = %s;
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, [user_id])
            # Fetch all rows and convert them to a list of dictionaries
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results
    except Exception as e:
        print(f"Error fetching user vouchers: {e}")
        return []

def get_promo_details(promo_code):
    """
    Fetch promo details by code.
    """
    query = """
        SELECT D.Discount, P.OfferEndDate
        FROM PROMO P
        INNER JOIN DISCOUNT D ON P.Code = D.Code
        WHERE P.Code = %s
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [promo_code])
        row = cursor.fetchone()
        if row:
            discount, offer_end_date = row
            return {"discount": discount, "offer_end_date": offer_end_date}
        return None

def render_booking_page(request, subcategory_id):
    """
    Render the booking page with promotions, sessions, and workers.
    """
    try:
        # Fetch the subcategory, sessions, and workers (your existing queries)
        # These are placeholders; replace them with your actual queries
        subcategory = get_subcategory(subcategory_id)  # Replace with actual logic
        sessions = get_sessions(subcategory_id)       # Replace with actual logic
        workers = get_workers(subcategory_id)         # Replace with actual logic

        # Fetch promotions
        query = """
            SELECT 
                p.Code AS promo_code,
                d.Discount AS discount_percentage,
                d.MinTrOrder AS min_transaction_order,
                p.OfferEndDate AS offer_end_date
            FROM 
                PROMO p
            INNER JOIN 
                DISCOUNT d ON p.Code = d.Code
            WHERE 
                p.OfferEndDate >= CURRENT_DATE
        """
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            promotions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return render(request, 'booking_page.html', {
            'subcategory': subcategory,
            'sessions': sessions,
            'workers': workers,
            'promotions': promotions,
        })
    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {e}'})


def fetch_promotions(request):
    query = """
        SELECT P.Code, D.Discount, P.OfferEndDate
        FROM PROMO P
        INNER JOIN DISCOUNT D ON P.Code = D.Code
        WHERE P.OfferEndDate >= CURRENT_DATE
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        promotions = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
    return JsonResponse({'promotions': promotions})


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection

@csrf_exempt
def create_testimonial(request):
    # Step 1: Fetch the logged-in user's details from the session
    user_id = request.session.get("user_id")  # Dynamically fetched user ID from the session
    if not user_id:
        return JsonResponse({'success': False, 'message': 'You must be logged in to submit a testimonial.'})

    if request.method == 'POST':
        try:
            # Step 2: Parse request data
            data = json.loads(request.body)
            worker_name = data.get('worker')
            rating = data.get('rating')
            comment = data.get('comment')

            # Validate inputs
            if not worker_name or not rating or not comment:
                return JsonResponse({'success': False, 'message': 'All fields are required.'})

            # Step 3: Fetch the username dynamically using the user_id
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT Name
                    FROM users
                    WHERE Id = %s
                """, [user_id])
                user_data = cursor.fetchone()
                if not user_data:
                    return JsonResponse({'success': False, 'message': 'User not found.'})
                
                user_name = user_data[0]  # Get the username dynamically

                # Step 4: Fetch the ServiceTrId for the worker
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

                # Step 5: Check if a testimonial already exists for today
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM TESTIMONI
                    WHERE ServiceTrId = %s AND date = CURRENT_DATE
                """, [service_tr_id])
                exists = cursor.fetchone()[0]

                if exists:
                    return JsonResponse({'success': False, 'message': 'A testimonial for this service order already exists today.'})

                # Step 6: Insert the testimonial into the TESTIMONI table
                cursor.execute("""
                    INSERT INTO TESTIMONI (ServiceTrId, date, Text, Rating)
                    VALUES (%s, CURRENT_DATE, %s, %s)
                """, [service_tr_id, comment, rating])

            # Step 7: Return success response with dynamic username
            return JsonResponse({
                'success': True,
                'message': 'Testimonial created successfully!',
                'username': user_name  # Return the dynamic username
            })

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})

import uuid

@csrf_exempt
@csrf_exempt
def create_testimonial_for_subcategory(request, subcategory_id: uuid.UUID):
    """
    Create a testimonial for a specific subcategory.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({'success': False, 'message': 'You must be logged in to create a testimonial.'})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            comment = data.get('comment')
            rating = data.get('rating')

            if not comment or not rating:
                return JsonResponse({'success': False, 'message': 'All fields are required.'})

            with connection.cursor() as cursor:
                # Fetch the most recent ServiceTrId (if it exists)
                cursor.execute("""
                    SELECT Id
                    FROM TR_SERVICE_ORDER
                    WHERE CustomerId = %s AND ServiceSubCategoryId = %s
                    ORDER BY ServiceDate DESC
                    LIMIT 1
                """, [user_id, subcategory_id])
                service_order = cursor.fetchone()

                # Use the ServiceTrId or a placeholder value
                service_tr_id = service_order[0] if service_order else "00000000-0000-0000-0000-000000000000"

                # Insert the testimonial
                cursor.execute("""
                    INSERT INTO TESTIMONI (ServiceTrId, date, Text, Rating)
                    VALUES (%s, CURRENT_DATE, %s, %s)
                """, [service_tr_id, comment, rating])

            return JsonResponse({'success': True, 'message': 'Testimonial created successfully!'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
