from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.db import connection
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import uuid


def main(request):
    return render(request, 'main.html')


@csrf_exempt
def register(request):
    if request.method == "GET":
        return render(request, "register.html")
    return redirect("register")

@csrf_exempt
def register_user(request):
    if request.method == "POST":
        # Get form data
        name = request.POST.get("name")
        sex = request.POST.get("sex")  # Should be 'M' or 'F'
        phone_number = request.POST.get("phone_number")
        password = request.POST.get("password")
        birthdate = request.POST.get("birthdate")
        address = request.POST.get("address")
        user_id = uuid.uuid4()

        # Validate required fields
        if not all([name, sex, phone_number, password, birthdate, address]):
            messages.error(request, "All fields are required.")
            return redirect("register_user")

        # Validate sex input
        if sex not in ['M', 'F']:
            messages.error(request, "Invalid value for sex. Please choose 'Male' or 'Female'.")
            return redirect("register_user")

        # Insert user into the database
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO users (id, name, sex, phonenum, pwd, dob, address, mypaybalance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [str(user_id), name, sex, phone_number, password, birthdate, address, 0])

        messages.success(request, "User registered successfully.")
        return redirect("login")

    return render(request, "register_user.html")

@csrf_exempt
def register_worker(request):
    if request.method == "POST":
        # Gather form data
        name = request.POST.get("name")
        password = request.POST.get("password")
        sex = request.POST.get("sex")
        phone_number = request.POST.get("phone_number")
        birthdate = request.POST.get("birthdate")
        address = request.POST.get("address")
        bank_name = request.POST.get("bank_name")
        account_number = request.POST.get("account_number")
        npwp = request.POST.get("npwp")
        pic_url = request.POST.get("pic_url")

        # Validate form input
        if not all([name, password, sex, phone_number, birthdate, address, bank_name, account_number, npwp, pic_url]):
            messages.error(request, "All fields are required.")
            return redirect("register_worker")

        if sex not in ['M', 'F']:
            messages.error(request, "Invalid sex selection. Please select 'M' or 'F'.")
            return redirect("register_worker")

        # Ensure the user is registering as a worker
        with connection.cursor() as cursor:
            # Check if phone number already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE PhoneNum = %s", [phone_number])
            if cursor.fetchone()[0] > 0:
                messages.error(request, "Phone number is already registered.")
                return redirect("register_worker")

            # Check if NPWP already exists
            cursor.execute("SELECT COUNT(*) FROM worker WHERE NPWP = %s", [npwp])
            if cursor.fetchone()[0] > 0:
                messages.error(request, "NPWP is already registered.")
                return redirect("register_worker")

            # Check if the bank account combination is unique
            cursor.execute("""
                SELECT COUNT(*) 
                FROM worker 
                WHERE BankName = %s AND AccNumber = %s
            """, [bank_name, account_number])
            if cursor.fetchone()[0] > 0:
                messages.error(request, "This Bank Name and Account Number combination is already registered.")
                return redirect("register_worker")

            # Create user and worker in a transaction
            user_id = uuid.uuid4()
            worker_id = str(user_id)  # Worker ID must match User ID as per schema design

            # Insert into users table
            cursor.execute("""
                INSERT INTO users (id, name, sex, phonenum, pwd, dob, address, mypaybalance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, [str(user_id), name, sex, phone_number, password, birthdate, address, 0])

            # Insert into worker table
            cursor.execute("""
                INSERT INTO worker (id, bankname, accnumber, npwp, picurl, rate, totalfinishorder)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [worker_id, bank_name, account_number, npwp, pic_url, 0, 0])

        # Confirm successful registration
        messages.success(request, "Worker registered successfully. Please log in.")
        return redirect("login")

    # Provide dropdown options for bank names
    bank_names = ["GoPay", "OVO", "Virtual Account BCA", "Virtual Account BNI", "Virtual Account Mandiri"]
    return render(request, "register_worker.html", {"bank_names": bank_names})


def login(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')

        with connection.cursor() as cursor:
            # Check for matching user in the database
            cursor.execute("""
                SELECT Id, Name, Pwd 
                FROM users 
                WHERE PhoneNum = %s
            """, [phone_number])
            user = cursor.fetchone()

            if user:
                user_id, user_name, stored_password = user

                # Check if the password matches
                if password == stored_password:  # Replace with hashed password verification if needed
                    # Save session data (convert UUID to string)
                    request.session['user_id'] = str(user_id)
                    request.session['user_name'] = user_name
                    return redirect('homepage')  # Redirect to the homepage after login
                else:
                    messages.error(request, "Invalid password. Please try again.")
            else:
                messages.error(request, "Invalid phone number or password. Please try again.")

        return redirect('login')

    return render(request, 'login.html')  # Display login form



def homepage(request):
    if 'user_id' not in request.session:
        return redirect('login')

    context = {'user_name': request.session.get('user_name')}
    return render(request, 'brian.html', context)


def logout(request):
    request.session.flush()
    return redirect('login')

@csrf_exempt
def user_profile(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return redirect("login")

    if request.method == "POST":
        name = request.POST.get("name")
        phone_number = request.POST.get("phone_number")
        sex = request.POST.get("sex")
        birthdate = request.POST.get("birthdate")
        address = request.POST.get("address")

        if not all([name, phone_number, sex, birthdate, address]):
            messages.error(request, "All fields are required.")
            return redirect("user_profile")

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET Name = %s, PhoneNum = %s, Sex = %s, DoB = %s, Address = %s 
                WHERE Id = %s
            """, [name, phone_number, sex, birthdate, address, user_id])

        messages.success(request, "Profile updated successfully.")
        return redirect("user_profile")

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT Name, PhoneNum, Sex, DoB, Address, MyPayBalance 
            FROM users 
            WHERE Id = %s
        """, [user_id])
        user_data = cursor.fetchone()

    profile_data = {
        "name": user_data[0],
        "phone_number": user_data[1],
        "sex": user_data[2],
        "birthdate": user_data[3],
        "address": user_data[4],
        "my_pay_balance": user_data[5],
    }

    return render(request, "user_profile.html", {"profile": profile_data})


@csrf_exempt
def worker_profile(request):
    worker_id = request.session.get("user_id")
    if not worker_id:
        return redirect("login")

    if request.method == "POST":
        name = request.POST.get("name")
        phone_number = request.POST.get("phone_number")
        sex = request.POST.get("sex")
        birthdate = request.POST.get("birthdate")
        address = request.POST.get("address")
        bank_name = request.POST.get("bank_name")
        account_number = request.POST.get("account_number")
        npwp = request.POST.get("npwp")

        if not all([name, phone_number, sex, birthdate, address, bank_name, account_number, npwp]):
            messages.error(request, "All fields are required.")
            return redirect("worker_profile")

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE users 
                SET Name = %s, PhoneNum = %s, Sex = %s, DoB = %s, Address = %s 
                WHERE Id = %s
            """, [name, phone_number, sex, birthdate, address, worker_id])

            cursor.execute("""
                UPDATE worker 
                SET BankName = %s, AccNumber = %s, NPWP = %s 
                WHERE Id = %s
            """, [bank_name, account_number, npwp, worker_id])

        messages.success(request, "Profile updated successfully.")
        return redirect("worker_profile")

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT u.Name, u.PhoneNum, u.Sex, u.DoB, u.Address, u.MyPayBalance, 
                   w.BankName, w.AccNumber, w.NPWP, w.Rate, w.TotalFinishOrder 
            FROM users u 
            JOIN worker w ON u.Id = w.Id 
            WHERE u.Id = %s
        """, [worker_id])
        worker_data = cursor.fetchone()

    profile_data = {
        "name": worker_data[0],
        "phone_number": worker_data[1],
        "sex": worker_data[2],
        "birthdate": worker_data[3],
        "address": worker_data[4],
        "my_pay_balance": worker_data[5],
        "bank_name": worker_data[6],
        "account_number": worker_data[7],
        "npwp": worker_data[8],
        "rate": worker_data[9],
        "total_finish_order": worker_data[10],
    }

    return render(request, "worker_profile.html", {"profile": profile_data})
