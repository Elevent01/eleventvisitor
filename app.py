import os
import random
import string
import logging
import uuid
import traceback
import json
import base64
import time 
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer
from flask import Flask, render_template, request, redirect, url_for, flash, session , jsonify 
import psycopg2
import bcrypt
from flask_wtf import CSRFProtect
from flask import request, jsonify
from dotenv import load_dotenv
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from datetime import datetime, date
from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField
from functools import wraps
from wtforms.csrf.core import CSRF

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('EMAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('EMAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
mail = Mail(app)

def get_db_connection():
    try:
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'dpg-d0cvgegdl3ps73ekdsi0-a'),
            database=os.getenv('DB_NAME', 'visitormanagement'),
            user=os.getenv('DB_USER', 'visitormanagement_user'),
            password=os.getenv('DB_PASSWORD', 'YeILqdZz6ZY6u4q0rUlBWKlRYHhTR5wF'),
            port=os.getenv('DB_PORT',5432)
        )
    except Exception as e:
        logging.error(f'Database connection error: {e}')
        return None

def generate_token(length=20):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.route('/')
def home():
    return redirect(url_for('login'))  # Redirect to login if that's the entry point

@app.route('/register_employee', methods=['GET', 'POST'])
def register_employee():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('login'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Check if the user has permission to register employees
            if not can_register_employee:
                flash('You do not have permission to register employees.', 'danger')
                return redirect(url_for('dashboard'))

            # Fetch company details to populate the dropdown
            cur.execute("SELECT CompanyID, CompanyName FROM CompanyDetails")
            companies = cur.fetchall()

            # Fetch all available roles
            cur.execute("SELECT role_id, role_name FROM Role ORDER BY role_name")
            roles = cur.fetchall()

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        conn.close()

    if request.method == 'POST':
        # Get form data
        employee_id = request.form.get('employee_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        department_id = request.form.get('department')
        designation_id = request.form.get('designation')
        phone_number = request.form.get('phone_number')
        date_of_birth = request.form.get('date_of_birth')
        date_of_joining = request.form.get('date_of_joining')
        address = request.form.get('address', '')
        company_id = request.form.get('company')
        role_id = request.form.get('role')
        status = True

        if not all([employee_id, first_name, last_name, email, department_id, 
                   designation_id, phone_number, date_of_birth, date_of_joining, 
                   company_id, role_id]):
            flash('All required fields must be filled.', 'danger')
            return redirect(url_for('register_employee'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('login'))

        try:
            with conn.cursor() as cur:
                # Get the department and designation names
                cur.execute("SELECT department_name FROM Department WHERE department_id = %s", (department_id,))
                department_result = cur.fetchone()
                if not department_result:
                    flash('Invalid department selected.', 'danger')
                    return render_template('register_employee.html',
                                        user_id=user_id,
                                        photo_filename=photo_filename,
                                        show_forget_password=show_forget_password,
                                        can_view_employees=can_view_employees,
                                        can_register_employee=can_register_employee,
                                        can_register_visitor=can_register_visitor,
                                        can_register_combined=can_register_combined,
                                        can_view_visitors=can_view_visitors,
                                        can_view_users=can_view_users,
                                        can_access_zone_requests=can_access_zone_requests,
                                        can_access_visitor_settings=can_access_visitor_settings,
                                        can_add_company=can_add_company,
                                        can_add_department=can_add_department,
                                        can_add_designation=can_add_designation,
                                        can_add_role=can_add_role,
                                        can_add_zone=can_add_zone,
                                        can_add_zone_area=can_add_zone_area,
                                        can_quick_register=can_quick_register,
                                        can_access_role_access=can_access_role_access,
                                        companies=companies,
                                        roles=roles)

                department_name = department_result[0]

                # Get designation name
                cur.execute("SELECT designation_name FROM DesignationMaster WHERE designation_id = %s", (designation_id,))
                designation_result = cur.fetchone()
                if not designation_result:
                    flash('Invalid designation selected.', 'danger')
                    return render_template('register_employee.html',
                                        user_id=user_id,
                                        photo_filename=photo_filename,
                                        show_forget_password=show_forget_password,
                                        can_view_employees=can_view_employees,
                                        can_register_employee=can_register_employee,
                                        can_register_visitor=can_register_visitor,
                                        can_register_combined=can_register_combined,
                                        can_view_visitors=can_view_visitors,
                                        can_view_users=can_view_users,
                                        can_access_zone_requests=can_access_zone_requests,
                                        can_access_visitor_settings=can_access_visitor_settings,
                                        can_add_company=can_add_company,
                                        can_add_department=can_add_department,
                                        can_add_designation=can_add_designation,
                                        can_add_role=can_add_role,
                                        can_add_zone=can_add_zone,
                                        can_add_zone_area=can_add_zone_area,
                                        can_quick_register=can_quick_register,
                                        can_access_role_access=can_access_role_access,
                                        companies=companies,
                                        roles=roles)

                designation_name = designation_result[0]

                # Fetch role access settings
                cur.execute("""
                    SELECT ShowForgetPassword, CanViewEmployees, CanRegisterEmployee,
                           CanRegisterVisitor, CanRegisterCombined, CanViewVisitors,
                           CanViewUsers, CanAccessZoneRequests, CanAccessVisitorSettings,
                           CanAddCompany, CanAddDepartment, CanAddDesignation,
                           CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                           CanAccessRoleAccess
                    FROM RoleAccess
                    WHERE company_id = %s AND role_id = %s
                """, (company_id, role_id))
                role_access = cur.fetchone()

                if not role_access:
                    flash('Invalid role selected.', 'danger')
                    return redirect(url_for('register_employee'))

                # Insert employee data
                cur.execute("""
                    INSERT INTO Employee (
                        Employee_Id, First_Name, Last_Name, Email, 
                        Designation, Department, PhoneNumber, 
                        DateOfBirth, DateOfJoining, Status, 
                        Address, Company
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s
                    )
                """, (
                    employee_id, first_name, last_name, email,
                    designation_name, department_name, phone_number,
                    date_of_birth, date_of_joining, status,
                    address, company_id
                ))

                # Insert into EmployeeRoles
                cur.execute("""
                    INSERT INTO EmployeeRoles (employee_id, company_id, role_id)
                    VALUES (%s, %s, %s)
                """, (employee_id, company_id, role_id))

                # Generate random password and create user account
                random_password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=8))
                hashed_password = bcrypt.hashpw(random_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Insert user with role-based permissions
                cur.execute("""
                    INSERT INTO Users (
                        UserId, Password, IsPasswordChange, ShowForgetPassword,
                        CanViewEmployees, CanRegisterEmployee, CanRegisterVisitor,
                        CanRegisterCombined, CanViewVisitors, CanViewUsers,
                        CanAccessZoneRequests, CanAccessVisitorSettings,
                        CanAddCompany, CanAddDepartment, CanAddDesignation,
                        CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                        CanAccessRoleAccess
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                """, (employee_id, hashed_password, False, *role_access))

                conn.commit()

                # Send welcome email
                msg = Message(
                    'Welcome to the System',
                    sender=os.getenv('EMAIL_USER'),
                    recipients=[email]
                )
                msg.body = (
                    f'Hello {first_name},\n\n'
                    f'Your account has been created successfully.\n'
                    f'Your temporary password is: {random_password}\n'
                    f'Please change your password after your first login.\n\n'
                    f'Best Regards,\nYour Company Name'
                )

                try:
                    mail.send(msg)
                    logging.info(f'Email sent to {email} with the random password.')
                except Exception as e:
                    logging.error(f'Error sending email: {e}')
                    flash('Employee registered, but failed to send email with the password.', 'warning')

                flash('Employee registered successfully! A random password has been generated for the user.', 'success')
                return redirect(url_for('dashboard'))

        except Exception as e:
            logging.error(f'Registration error: {e}')
            flash('An error occurred while registering the employee. Please try again.', 'danger')
            conn.rollback()
        finally:
            conn.close()

    return render_template('register_employee.html', 
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         companies=companies,
                         roles=roles)

@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    # Ensure user is authenticated and user ID is available
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to add a department.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        # Fetch user information for settings
        with conn.cursor() as cur:
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Check if user has permission to add departments
            if not can_add_department:
                flash('You do not have permission to add departments.', 'danger')
                return redirect(url_for('dashboard'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Fetch all companies for displaying in the dropdown
            cur.execute("""
                SELECT CompanyID, CompanyName
                FROM CompanyDetails
            """)
            companies = cur.fetchall()

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    # Handle form submission for adding a new department
    if request.method == 'POST':
        # Retrieve data from the form
        department_name = request.form.get('departmentName')
        company_id = request.form.get('companyId')

        # Validate required fields
        if not all([department_name, company_id]):
            flash('Department name and company are required.', 'danger')
            return redirect(url_for('add_department'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('add_department'))

        try:
            with conn.cursor() as cur:
                # Remove all spaces from the input department name for comparison
                cleaned_input_name = department_name.replace(" ", "").lower()

                # Get all existing departments for this company
                cur.execute("""
                    SELECT department_name FROM Department 
                    WHERE company_id = %s
                """, (company_id,))
                existing_departments = cur.fetchall()

                # Check if any existing department name matches (ignoring spaces)
                for dept in existing_departments:
                    existing_cleaned_name = dept[0].replace(" ", "").lower()
                    if cleaned_input_name == existing_cleaned_name:
                        flash('Department name already exists (ignoring spaces). Please choose a different name.', 'danger')
                        return redirect(url_for('add_department'))

                # Insert the new department into the database
                cur.execute("""
                    INSERT INTO Department (department_name, company_id, created_at)
                    VALUES (%s, %s, %s)
                """, (department_name, company_id, datetime.now()))
                conn.commit()

                flash('Department added successfully!', 'success')
                return redirect(url_for('add_department'))

        except Exception as e:
            logging.error(f'Error adding department: {e}')
            flash('An error occurred while adding the department. Please try again.', 'danger')
            return redirect(url_for('add_department'))
        finally:
            if conn:
                conn.close()

    # Render the form template with all necessary data
    return render_template('add_department.html', 
                         companies=companies,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

@app.route('/get_departments/<int:company_id>')
def get_departments(company_id):
    conn = get_db_connection()
    departments = []
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT department_id, department_name
                FROM Department
                WHERE company_id = %s
                ORDER BY department_name
            """, (company_id,))
            departments = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
    except Exception as e:
        logging.error(f'Error fetching departments: {e}')
    finally:
        if conn:
            conn.close()
    
    return jsonify(departments)


@app.route('/edit_department', methods=['POST'])
def edit_department():
    # Ensure user is authenticated and user ID is available
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to edit a department.', 'danger')
        return redirect(url_for('login'))

    # Get department ID and name from the form data
    department_id = request.form.get('departmentId')
    department_name = request.form.get('departmentName')

    if not department_id or not department_name:
        flash('Invalid department data.', 'danger')
        return redirect(url_for('add_department'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('add_department'))

    try:
        with conn.cursor() as cur:
            # Update department name in the database
            cur.execute("""
                UPDATE Department
                SET department_name = %s
                WHERE department_id = %s
            """, (department_name, department_id))
            conn.commit()

            flash('Department name updated successfully!', 'success')
            return redirect(url_for('add_department'))

    except Exception as e:
        logging.error(f'Error updating department: {e}')
        flash('An error occurred while updating the department. Please try again.', 'danger')
        return redirect(url_for('add_department'))

    finally:
        if conn:
            conn.close()


@app.route('/add_designation', methods=['GET', 'POST'])
def add_designation():
    # Ensure user is authenticated and user ID is available
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to add a designation.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        # Fetch user information for settings
        with conn.cursor() as cur:
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Fetch all companies
            cur.execute("""
                SELECT CompanyID, CompanyName
                FROM CompanyDetails
                ORDER BY CompanyName
            """)
            companies = cur.fetchall()

            # Fetch all designations with company and department info
            cur.execute("""
                SELECT 
                    dm.designation_id,
                    dm.designation_name,
                    cd.CompanyID as company_id,
                    cd.CompanyName as company_name,
                    d.department_id,
                    d.department_name
                FROM DesignationMaster dm
                JOIN DepartmentDesignation dd ON dm.designation_id = dd.designation_id
                JOIN Department d ON dd.department_id = d.department_id
                JOIN CompanyDetails cd ON d.company_id = cd.CompanyID
                ORDER BY cd.CompanyName, d.department_name, dm.designation_name
            """)
            designations = [
                {
                    'designation_id': row[0],
                    'designation_name': row[1],
                    'company_id': row[2],
                    'company_name': row[3],
                    'department_id': row[4],
                    'department_name': row[5]
                }
                for row in cur.fetchall()
            ]

    except Exception as e:
        logging.error(f'Error fetching initial data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    # Handle form submission for adding a new designation
    if request.method == 'POST':
        # Retrieve data from the form
        designation_name = request.form.get('designationName')
        department_id = request.form.get('departmentId')

        # Validate required fields
        if not all([designation_name, department_id]):
            flash('Designation name and department are required.', 'danger')
            return redirect(url_for('add_designation'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('add_designation'))

        try:
            with conn.cursor() as cur:
                # Remove spaces and convert to lowercase for comparison
                cleaned_designation_name = designation_name.replace(" ", "").lower()

                # First check if this designation exists in the master table
                cur.execute("""
                    SELECT designation_id, designation_name 
                    FROM DesignationMaster 
                    WHERE LOWER(REPLACE(designation_name, ' ', '')) = %s
                """, (cleaned_designation_name,))
                designation_master = cur.fetchone()

                designation_id = None
                if designation_master:
                    designation_id = designation_master[0]
                    # Check if this designation is already assigned to this department
                    cur.execute("""
                        SELECT COUNT(*) FROM DepartmentDesignation 
                        WHERE designation_id = %s AND department_id = %s
                    """, (designation_id, department_id))
                    exists_in_department = cur.fetchone()[0] > 0

                    if exists_in_department:
                        flash('This designation is already assigned to this department.', 'danger')
                        return redirect(url_for('add_designation'))
                else:
                    # Create new designation in master table
                    cur.execute("""
                        INSERT INTO DesignationMaster (designation_name, created_at)
                        VALUES (%s, %s)
                        RETURNING designation_id
                    """, (designation_name, datetime.now()))
                    designation_id = cur.fetchone()[0]

                # Assign designation to department
                cur.execute("""
                    INSERT INTO DepartmentDesignation (department_id, designation_id, created_at)
                    VALUES (%s, %s, %s)
                """, (department_id, designation_id, datetime.now()))
                
                conn.commit()
                flash('Designation added successfully!', 'success')
                return redirect(url_for('add_designation'))

        except Exception as e:
            logging.error(f'Error adding designation: {e}')
            flash('An error occurred while adding the designation. Please try again.', 'danger')
            return redirect(url_for('add_designation'))
        finally:
            conn.close()

    return render_template('add_designation.html', 
                         companies=companies,
                         designations=designations,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)


@app.route('/edit_designation', methods=['POST'])
def edit_designation():
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to edit a designation.', 'danger')
        return redirect(url_for('login'))

    designation_id = request.form.get('designationId')
    designation_name = request.form.get('designationName')

    if not designation_id or not designation_name:
        flash('Invalid designation data.', 'danger')
        return redirect(url_for('add_designation'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('add_designation'))

    try:
        with conn.cursor() as cur:
            # First get current department_id and company_id
            cur.execute("""
                SELECT dd.department_id, d.company_id
                FROM DepartmentDesignation dd
                JOIN Department d ON dd.department_id = d.department_id
                WHERE dd.designation_id = %s
            """, (designation_id,))
            result = cur.fetchone()
            
            if not result:
                flash('Designation not found.', 'danger')
                return redirect(url_for('add_designation'))
                
            department_id, company_id = result

            # Update designation name in master table
            cur.execute("""
                UPDATE DesignationMaster 
                SET designation_name = %s
                WHERE designation_id = %s
            """, (designation_name, designation_id))

            conn.commit()
            flash('Designation updated successfully!', 'success')
            return redirect(url_for('add_designation'))

    except Exception as e:
        logging.error(f'Error updating designation: {e}')
        flash('An error occurred while updating the designation.', 'danger')
        return redirect(url_for('add_designation'))
    finally:
        if conn:
            conn.close()

@app.route('/get_designations/<int:department_id>')
def get_designations(department_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        with conn.cursor() as cur:
            # Get designations from DesignationMaster through DepartmentDesignation
            cur.execute("""
                SELECT dm.designation_id, dm.designation_name
                FROM DesignationMaster dm
                JOIN DepartmentDesignation dd ON dm.designation_id = dd.designation_id
                WHERE dd.department_id = %s
                ORDER BY dm.designation_name
            """, (department_id,))
            designations = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
            return jsonify(designations)

    except Exception as e:
        logging.error(f'Error fetching designations: {e}')
        return jsonify({'error': 'An error occurred while fetching designations'}), 500
    finally:
        conn.close()
        
@app.route('/add_role', methods=['GET', 'POST'])
def add_role():
    user_id = session.get('user_id')
    if not user_id:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'You need to be logged in to add a role.'})
        flash('You need to be logged in to add a role.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'Database connection error.'})
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                if request.method == 'POST':
                    return jsonify({'success': False, 'message': 'User not found.'})
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Unpack user permissions
            (user_id, show_forget_password, can_view_employees,
             can_register_employee, can_register_visitor,
             can_register_combined, can_view_visitors, can_view_users,
             can_access_zone_requests, can_access_visitor_settings,
             can_add_company, can_add_department, can_add_designation,
             can_add_role, can_add_zone, can_add_zone_area,
             can_quick_register, can_access_role_access) = user

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Fetch existing roles
            cur.execute("SELECT role_id, role_name FROM Role ORDER BY role_name")
            existing_roles = cur.fetchall()

            if request.method == 'POST':
                role_name = request.form.get('roleName')
                
                if not role_name:
                    return jsonify({'success': False, 'message': 'Role name is required.'})

                # Remove all spaces from the input role name for comparison
                cleaned_input_name = role_name.replace(" ", "").lower()

                # Check if the role already exists
                cur.execute("SELECT role_name FROM Role")
                existing_roles = cur.fetchall()

                # Check for duplicate roles (ignoring spaces)
                if any(role[0].replace(" ", "").lower() == cleaned_input_name 
                      for role in existing_roles):
                    return jsonify({
                        'success': False,
                        'message': 'Role name already exists (ignoring spaces). Please choose a different name.'
                    })

                # Insert the new role
                cur.execute("""
                    INSERT INTO Role (role_name, created_at)
                    VALUES (%s, %s)
                    RETURNING role_id, role_name
                """, (role_name, datetime.now()))
                new_role = cur.fetchone()
                conn.commit()

                return jsonify({
                    'success': True,
                    'message': 'Role added successfully!',
                    'role': {
                        'role_id': new_role[0],
                        'role_name': new_role[1]
                    }
                })

    except Exception as e:
        logging.error(f'Error in add_role: {e}')
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('add_role'))
    finally:
        conn.close()

    return render_template('add_role.html',
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         existing_roles=existing_roles)

@app.route('/edit_role', methods=['POST'])
def edit_role():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'You need to be logged in to edit a role.'})

    try:
        data = request.json
        role_id = data.get('roleId')
        new_role_name = data.get('roleName')

        if not role_id or not new_role_name:
            return jsonify({'success': False, 'message': 'Role ID and name are required.'})

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Database connection error.'})

        with conn.cursor() as cur:
            # Remove all spaces from the input role name for comparison
            cleaned_input_name = new_role_name.replace(" ", "").lower()

            # Check if the role name already exists (excluding the current role)
            cur.execute("SELECT role_name FROM Role WHERE role_id != %s", (role_id,))
            existing_roles = cur.fetchall()

            # Check for duplicate roles (ignoring spaces)
            if any(role[0].replace(" ", "").lower() == cleaned_input_name 
                  for role in existing_roles):
                return jsonify({
                    'success': False, 
                    'message': 'Role name already exists (ignoring spaces). Please choose a different name.'
                })

            # Update the role name (removed updated_at column)
            cur.execute("""
                UPDATE Role 
                SET role_name = %s
                WHERE role_id = %s
            """, (new_role_name, role_id))
            conn.commit()

            return jsonify({'success': True, 'message': 'Role updated successfully!'})

    except Exception as e:
        logging.error(f'Error in edit_role: {e}')
        return jsonify({'success': False, 'message': 'An error occurred while updating the role.'})
    finally:
        if conn:
            conn.close()

@app.route('/get_roles', methods=['GET'])
def get_roles():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role_id, role_name
                FROM Role
                ORDER BY role_name
            """)
            roles = cur.fetchall()
            return jsonify([{'role_id': role[0], 'role_name': role[1]} for role in roles])

    except Exception as e:
        logging.error(f'Error fetching roles: {e}')
        return jsonify({'error': 'An error occurred while fetching roles'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'user_id' not in session:
        flash('You need to be logged in to upload a photo.', 'danger')
        return redirect(url_for('dashboard'))  # Redirect to login or appropriate page

    if 'photo' not in request.files:
        flash('No photo uploaded.', 'danger')
        return redirect(url_for('dashboard'))

    photo = request.files['photo']
    if photo.filename == '':
        flash('No selected photo.', 'danger')
        return redirect(url_for('dashboard'))

    user_id = session['user_id']
    conn = get_db_connection()
    
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch the existing photo filename
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            existing_photo = cur.fetchone()
            existing_photo_filename = existing_photo[0] if existing_photo else None

            # If an existing photo is found, delete it from the filesystem
            if existing_photo_filename:
                existing_photo_path = os.path.join('static/profile_photos', existing_photo_filename)
                if os.path.exists(existing_photo_path):
                    os.remove(existing_photo_path)

            # Generate a new filename for the new photo
            photo_filename = f"{uuid.uuid4().hex}_{photo.filename}"
            photo_path = os.path.join('static/profile_photos', photo_filename)
            photo.save(photo_path)

            # Update the database with the new photo filename
            cur.execute("UPDATE Employee SET Photo = %s WHERE Employee_Id = %s", (photo_filename, user_id))
            conn.commit()
        flash('Photo uploaded successfully!', 'success')
    except Exception as e:
        logging.error(f'Error uploading photo: {e}')
        flash('An error occurred while uploading the photo. Please try again.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))
# Initialize the serializer for token generation
s = URLSafeTimedSerializer('your-secret-key')

@app.route('/request_reset', methods=['GET', 'POST'])
def request_reset():
    if request.method == 'POST':
        user_id = request.form['user_id']
        email = request.form['email']
        
        logging.info(f"Password reset requested for user_id: {user_id}, email: {email}")

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('request_reset'))

        try:
            with conn.cursor() as cur:
                # First check if user exists and get ShowForgetPassword status
                cur.execute("SELECT ShowForgetPassword FROM Users WHERE UserId = %s", (user_id,))
                user_record = cur.fetchone()
                
                if user_record:
                    show_forget_password = user_record[0]
                    logging.info(f"ShowForgetPassword value for user {user_id}: {show_forget_password}")

                    # Convert to boolean if needed
                    if isinstance(show_forget_password, (int, str)):
                        show_forget_password = bool(int(show_forget_password))

                    # Only proceed if ShowForgetPassword is False
                    if show_forget_password:
                        logging.info(f"Password reset blocked for user {user_id} - ShowForgetPassword is True")
                        flash('Password reset is not available for this account.', 'danger')
                        return redirect(url_for('request_reset'))

                    # Check the email and status in the Employee table
                    cur.execute("SELECT Email, Status FROM Employee WHERE Employee_Id = %s", (user_id,))
                    employee_record = cur.fetchone()
                    
                    if employee_record:
                        db_email, status = employee_record
                        if db_email == email:
                            if not status:  # Check if the status is inactive
                                flash('Your account is inactive. Password reset cannot be processed.', 'danger')
                                return redirect(url_for('request_reset'))

                            # Generate password reset token
                            token = s.dumps(email, salt='password-reset-salt')
                            reset_link = f'http://localhost:5000/reset_password/{token}'
                            
                            msg = Message('Password Reset Request', 
                                        sender=os.getenv('EMAIL_USER'), 
                                        recipients=[email])
                            msg.body = f'''
                            Click the link to reset your password: {reset_link}
                            
                            If you did not request this password reset, please ignore this email.
                            This link will expire in 1 hour.
                            '''
                            
                            try:
                                mail.send(msg)
                                logging.info(f'Password reset email sent to {email}.')
                                flash('Check your email for a password reset link.', 'info')
                                return redirect(url_for('login'))
                            except Exception as e:
                                logging.error(f'Error sending password reset email: {e}')
                                flash('An error occurred while sending the email. Please try again.', 'danger')
                        else:
                            flash('User ID and email do not match.', 'danger')
                    else:
                        flash('User ID not found in Employee records.', 'danger')
                else:
                    flash('User ID does not exist.', 'danger')

        except Exception as e:
            logging.error(f'Request reset error: {e}')
            flash('An error occurred while processing your request. Please try again.', 'danger')
        finally:
            conn.close()

    return render_template('request_reset.html')



@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='password-reset-salt', max_age=3600)  # Token expires in 1 hour
    except Exception:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password == confirm_password:
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn = get_db_connection()
            if conn is None:
                flash('Database connection error. Please try again later.', 'danger')
                return redirect(url_for('index'))

            try:
                with conn.cursor() as cur:
                    cur.execute(""" 
                        UPDATE Users 
                        SET Password = %s, IsPasswordChange = %s 
                        WHERE UserId IN (SELECT Employee_Id FROM Employee WHERE Email = %s)
                    """, (hashed_password, True, email))
                    conn.commit()
                    flash('Your password has been updated!', 'success')
                    return redirect(url_for('login'))
            except Exception as e:
                logging.error(f'Password reset error: {e}')
                flash('An error occurred while updating your password. Please try again.', 'danger')
            finally:
                conn.close()
        else:
            flash('New password and confirmation do not match.', 'danger')

    return render_template('reset_password.html', token=token)

# Define User class to encapsulate user-related logic
class User:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_user_details(self, conn):
        # Fetch user details like password and whether the password has been changed
        with conn.cursor() as cur:
            cur.execute("SELECT Password, IsPasswordChange FROM Users WHERE UserId = %s", (self.user_id,))
            return cur.fetchone()


# Define Employee class to encapsulate employee-related logic
class Employee:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_employee_status(self, conn):
        # Fetch employee status (active or inactive)
        with conn.cursor() as cur:
            cur.execute("SELECT Status FROM Employee WHERE Employee_Id = %s", (self.user_id,))
            return cur.fetchone()


# Define Authenticator class to handle authentication logic
class Authenticator:
    def __init__(self, user, password):
        self.user = user
        self.password = password

    def authenticate(self, conn):
        # Fetch user details (password and change status)
        user_details = self.user.get_user_details(conn)
        if not user_details:
            return False

        hashed_password, is_password_changed = user_details

        # Verify password
        if bcrypt.checkpw(self.password.encode('utf-8'), hashed_password.encode('utf-8')):
            return True
        return False


# Define the login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('login'))

        try:
            # Create User and Employee objects
            user = User(user_id)
            employee = Employee(user_id)

            # Authenticate user using Authenticator class
            authenticator = Authenticator(user, password)
            if not authenticator.authenticate(conn):
                flash('Invalid credentials.', 'danger')
                return redirect(url_for('login'))

            # Check employee status
            employee_status = employee.get_employee_status(conn)
            if not employee_status or not employee_status[0]:
                flash('Your account is inactive. Please contact support.', 'danger')
                return redirect(url_for('login'))

            # Successful login
            flash('Login successful!', 'success')
            session['user_id'] = user_id  # Set user ID in session
            return redirect(url_for('dashboard'))

        except Exception as e:
            logging.error(f'Login error: {e}')
            flash('An error occurred during login. Please try again.', 'danger')
        finally:
            conn.close()

    return render_template('login.html')



@app.route('/dashboard')
def dashboard():
    logging.info("Accessing dashboard route")
    
    user_id = None
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            logging.warning("No user_id found in session")
            flash('Please log in to access the dashboard.', 'warning')
            return redirect(url_for('login'))
        
        conn = None
        for attempt in range(3):
            try:
                conn = get_db_connection()
                if conn:
                    break
            except Exception as db_err:
                logging.error(f"Database connection attempt {attempt + 1} failed: {db_err}")
                time.sleep(1)
        
        if not conn:
            logging.critical("Failed to establish database connection")
            flash('Unable to connect to the database. Please try again later.', 'danger')
            return redirect(url_for('login'))
        
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        UserId, 
                        ShowForgetPassword, 
                        CanViewEmployees, 
                        CanRegisterEmployee, 
                        CanRegisterVisitor, 
                        CanRegisterCombined, 
                        CanViewVisitors, 
                        CanViewUsers, 
                        CanAccessZoneRequests, 
                        CanAccessVisitorSettings,
                        CanAddCompany,
                        CanAddDepartment,
                        CanAddDesignation,
                        CanAddRole,
                        CanAddZone,
                        CanAddZoneArea,
                        CanQuickRegister,
                        CanAccessRoleAccess
                    FROM Users 
                    WHERE UserId = %s
                """, (user_id,))
                
                user = cur.fetchone()
                
                user_data = {
                    'user_id': user_id,
                    'show_forget_password': False,
                    'can_view_employees': False,
                    'can_register_employee': False,
                    'can_register_visitor': False,
                    'can_register_combined': False,
                    'can_view_visitors': False,
                    'can_view_users': False,
                    'can_access_zone_requests': False,
                    'can_access_visitor_settings': False,
                    'can_add_company': False,
                    'can_add_department': False,
                    'can_add_designation': False,
                    'can_add_role': False,
                    'can_add_zone': False,
                    'can_add_zone_area': False,
                    'can_quick_register': False,
                    'can_access_role_access': False,
                    'photo_filename': None
                }
                
                if user:
                    user_data.update({
                        'user_id': user[0],
                        'show_forget_password': bool(user[1]),
                        'can_view_employees': bool(user[2]),
                        'can_register_employee': bool(user[3]),
                        'can_register_visitor': bool(user[4]),
                        'can_register_combined': bool(user[5]),
                        'can_view_visitors': bool(user[6]),
                        'can_view_users': bool(user[7]),
                        'can_access_zone_requests': bool(user[8]),
                        'can_access_visitor_settings': bool(user[9]),
                        'can_add_company': bool(user[10]),
                        'can_add_department': bool(user[11]),
                        'can_add_designation': bool(user[12]),
                        'can_add_role': bool(user[13]),
                        'can_add_zone': bool(user[14]),
                        'can_add_zone_area': bool(user[15]),
                        'can_quick_register': bool(user[16]),
                        'can_access_role_access': bool(user[17])
                    })
                else:
                    logging.warning(f"No user found for user_id: {user_id}")
                    flash('User account not found.', 'danger')
                    return redirect(url_for('login'))
                
                cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
                photo_result = cur.fetchone()
                if photo_result:
                    user_data['photo_filename'] = photo_result[0]
        
        except Exception as fetch_err:
            logging.error(f"Error fetching user data: {fetch_err}")
            flash('Error retrieving your account information.', 'danger')
            return redirect(url_for('login'))
        
        finally:
            if conn:
                conn.close()
        
        return render_template(
            'dashboard.html', 
            user_id=user_data['user_id'], 
            show_forget_password=user_data['show_forget_password'], 
            can_view_employees=user_data['can_view_employees'], 
            can_register_employee=user_data['can_register_employee'], 
            can_register_visitor=user_data['can_register_visitor'], 
            can_register_combined=user_data['can_register_combined'], 
            can_view_visitors=user_data['can_view_visitors'], 
            can_view_users=user_data['can_view_users'], 
            can_access_zone_requests=user_data['can_access_zone_requests'], 
            can_access_visitor_settings=user_data['can_access_visitor_settings'],
            can_add_company=user_data['can_add_company'],
            can_add_department=user_data['can_add_department'],
            can_add_designation=user_data['can_add_designation'],
            can_add_role=user_data['can_add_role'],
            can_add_zone=user_data['can_add_zone'],
            can_add_zone_area=user_data['can_add_zone_area'],
            can_quick_register=user_data['can_quick_register'],
            can_access_role_access=user_data['can_access_role_access'],
            photo_filename=user_data['photo_filename'],
            current_page_name='Dashboard'
        )
    
    except Exception as main_err:
        logging.critical(f"Unexpected error in dashboard route: {main_err}")
        flash('An unexpected error occurred. Please try again.', 'danger')
        return redirect(url_for('login'))


@app.route('/users', methods=['GET'])
def view_users():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
               SELECT UserId, ShowForgetPassword, CanViewEmployees,
                      CanRegisterEmployee, CanRegisterVisitor, 
                      CanRegisterCombined, CanViewVisitors, CanViewUsers,
                      CanAccessZoneRequests, CanAccessVisitorSettings,
                      CanAddCompany, CanAddDepartment, CanAddDesignation,
                      CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                      CanAccessRoleAccess, CanGiveRoleAccess
               FROM Users 
               WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Unpack user permissions
            (user_id, show_forget_password, can_view_employees,
             can_register_employee, can_register_visitor,
             can_register_combined, can_view_visitors, can_view_users,
             can_access_zone_requests, can_access_visitor_settings,
             can_add_company, can_add_department, can_add_designation,
             can_add_role, can_add_zone, can_add_zone_area, can_quick_register,
             can_access_role_access, can_give_role_access) = user

            # Check if the user has permission to view users
            if not can_view_users:
                flash('You do not have permission to view users.', 'danger')
                return redirect(url_for('dashboard'))

            # Fetch all users
            cur.execute("""
                SELECT Id, UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, CanRegisterCombined,
                       CanViewVisitors, CanViewUsers, CanAccessZoneRequests,
                       CanAccessVisitorSettings, CanAddCompany, CanAddDepartment,
                       CanAddDesignation, CanAddRole, CanAddZone, CanAddZoneArea,
                       CanQuickRegister, CanAccessRoleAccess
                FROM Users
                ORDER BY UserId
            """)
            users = cur.fetchall()

            # Fetch all company names
            cur.execute("SELECT CompanyName FROM CompanyDetails ORDER BY CompanyName")
            companies = [company[0] for company in cur.fetchall()]

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Convert users to list of dictionaries for easier template handling
            user_list = []
            for user in users:
                user_dict = {
                    'Id': user[0],
                    'UserId': user[1],
                    'ShowForgetPassword': user[2],
                    'CanViewEmployees': user[3],
                    'CanRegisterEmployee': user[4],
                    'CanRegisterVisitor': user[5],
                    'CanRegisterCombined': user[6],
                    'CanViewVisitors': user[7],
                    'CanViewUsers': user[8],
                    'CanAccessZoneRequests': user[9],
                    'CanAccessVisitorSettings': user[10],
                    'CanAddCompany': user[11],
                    'CanAddDepartment': user[12],
                    'CanAddDesignation': user[13],
                    'CanAddRole': user[14],
                    'CanAddZone': user[15],
                    'CanAddZoneArea': user[16],
                    'CanQuickRegister': user[17],
                    'CanAccessRoleAccess': user[18]
                }
                user_list.append(user_dict)

            return render_template('view_users.html', 
                                users=user_list,
                                companies=companies,
                                user_id=user_id,
                                photo_filename=photo_filename,
                                show_forget_password=show_forget_password,
                                can_view_employees=can_view_employees,
                                can_register_employee=can_register_employee,
                                can_register_visitor=can_register_visitor,
                                can_register_combined=can_register_combined,
                                can_view_visitors=can_view_visitors,
                                can_view_users=can_view_users,
                                can_access_zone_requests=can_access_zone_requests,
                                can_access_visitor_settings=can_access_visitor_settings,
                                can_add_company=can_add_company,
                                can_add_department=can_add_department,
                                can_add_designation=can_add_designation,
                                can_add_role=can_add_role,
                                can_add_zone=can_add_zone,
                                can_add_zone_area=can_add_zone_area,
                                can_quick_register=can_quick_register,
                                can_access_role_access=can_access_role_access)

    except Exception as e:
        logging.error(f'Error fetching users: {str(e)}')
        flash('An error occurred while fetching users. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

    finally:
        if conn:
            conn.close()

@app.route('/get_company_roles/<int:company_id>')
def get_company_roles(company_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify([])

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT r.role_id, r.role_name
                FROM Role r
                JOIN RoleAccess ra ON r.role_id = ra.role_id
                WHERE ra.company_id = %s
                ORDER BY r.role_name
            """, (company_id,))
            roles = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
            return jsonify(roles)
    except Exception as e:
        logging.error(f'Error fetching roles: {e}')
        return jsonify([])
    finally:
        conn.close()

@app.route('/role_access', methods=['GET', 'POST'])
def role_access():
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to manage role access.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Fetch all companies
            cur.execute("SELECT CompanyID, CompanyName FROM CompanyDetails ORDER BY CompanyName")
            companies = cur.fetchall()

            # Fetch all roles
            cur.execute("SELECT role_id, role_name FROM Role ORDER BY role_name")
            roles = cur.fetchall()

            if request.method == 'POST':
                data = request.get_json()
                if not data:
                    data = request.form

                company_id = data.get('company_id')
                role_id = data.get('role_id')

                if not company_id or not role_id:
                    if request.content_type == 'application/json':
                        return jsonify({'error': 'Company ID and Role ID are required'}), 400
                    flash('Company and Role selection is required.', 'danger')
                    return redirect(url_for('role_access'))

                # Get all permission fields
                permissions = {
                    'ShowForgetPassword': data.get('showForgetPassword') in ['true', 'on', True],
                    'CanViewEmployees': data.get('canViewEmployees') in ['true', 'on', True],
                    'CanRegisterEmployee': data.get('canRegisterEmployee') in ['true', 'on', True],
                    'CanRegisterVisitor': data.get('canRegisterVisitor') in ['true', 'on', True],
                    'CanRegisterCombined': data.get('canRegisterCombined') in ['true', 'on', True],
                    'CanViewVisitors': data.get('canViewVisitors') in ['true', 'on', True],
                    'CanViewUsers': data.get('canViewUsers') in ['true', 'on', True],
                    'CanAccessZoneRequests': data.get('canAccessZoneRequests') in ['true', 'on', True],
                    'CanAccessVisitorSettings': data.get('canAccessVisitorSettings') in ['true', 'on', True],
                    'CanAddCompany': data.get('canAddCompany') in ['true', 'on', True],
                    'CanAddDepartment': data.get('canAddDepartment') in ['true', 'on', True],
                    'CanAddDesignation': data.get('canAddDesignation') in ['true', 'on', True],
                    'CanAddRole': data.get('canAddRole') in ['true', 'on', True],
                    'CanAddZone': data.get('canAddZone') in ['true', 'on', True],
                    'CanAddZoneArea': data.get('canAddZoneArea') in ['true', 'on', True],
                    'CanQuickRegister': data.get('canQuickRegister') in ['true', 'on', True],
                    'CanAccessRoleAccess': data.get('canAccessRoleAccess') in ['true', 'on', True]
                }

                # First update the RoleAccess table
                update_role_access_query = """
                    INSERT INTO RoleAccess (
                        company_id, role_id,
                        ShowForgetPassword, CanViewEmployees,
                        CanRegisterEmployee, CanRegisterVisitor,
                        CanRegisterCombined, CanViewVisitors,
                        CanViewUsers, CanAccessZoneRequests,
                        CanAccessVisitorSettings, CanAddCompany,
                        CanAddDepartment, CanAddDesignation,
                        CanAddRole, CanAddZone,
                        CanAddZoneArea, CanQuickRegister,
                        CanAccessRoleAccess, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (company_id, role_id) DO UPDATE SET
                        ShowForgetPassword = EXCLUDED.ShowForgetPassword,
                        CanViewEmployees = EXCLUDED.CanViewEmployees,
                        CanRegisterEmployee = EXCLUDED.CanRegisterEmployee,
                        CanRegisterVisitor = EXCLUDED.CanRegisterVisitor,
                        CanRegisterCombined = EXCLUDED.CanRegisterCombined,
                        CanViewVisitors = EXCLUDED.CanViewVisitors,
                        CanViewUsers = EXCLUDED.CanViewUsers,
                        CanAccessZoneRequests = EXCLUDED.CanAccessZoneRequests,
                        CanAccessVisitorSettings = EXCLUDED.CanAccessVisitorSettings,
                        CanAddCompany = EXCLUDED.CanAddCompany,
                        CanAddDepartment = EXCLUDED.CanAddDepartment,
                        CanAddDesignation = EXCLUDED.CanAddDesignation,
                        CanAddRole = EXCLUDED.CanAddRole,
                        CanAddZone = EXCLUDED.CanAddZone,
                        CanAddZoneArea = EXCLUDED.CanAddZoneArea,
                        CanQuickRegister = EXCLUDED.CanQuickRegister,
                        CanAccessRoleAccess = EXCLUDED.CanAccessRoleAccess,
                        updated_at = CURRENT_TIMESTAMP
                """
                
                role_access_params = [
                    company_id, role_id,
                    permissions['ShowForgetPassword'],
                    permissions['CanViewEmployees'],
                    permissions['CanRegisterEmployee'],
                    permissions['CanRegisterVisitor'],
                    permissions['CanRegisterCombined'],
                    permissions['CanViewVisitors'],
                    permissions['CanViewUsers'],
                    permissions['CanAccessZoneRequests'],
                    permissions['CanAccessVisitorSettings'],
                    permissions['CanAddCompany'],
                    permissions['CanAddDepartment'],
                    permissions['CanAddDesignation'],
                    permissions['CanAddRole'],
                    permissions['CanAddZone'],
                    permissions['CanAddZoneArea'],
                    permissions['CanQuickRegister'],
                    permissions['CanAccessRoleAccess'],
                    datetime.now()
                ]

                cur.execute(update_role_access_query, role_access_params)

                # Now update all users who have this role in this company
                update_users_query = """
                    UPDATE Users u
                    SET 
                        ShowForgetPassword = %s,
                        CanViewEmployees = %s,
                        CanRegisterEmployee = %s,
                        CanRegisterVisitor = %s,
                        CanRegisterCombined = %s,
                        CanViewVisitors = %s,
                        CanViewUsers = %s,
                        CanAccessZoneRequests = %s,
                        CanAccessVisitorSettings = %s,
                        CanAddCompany = %s,
                        CanAddDepartment = %s,
                        CanAddDesignation = %s,
                        CanAddRole = %s,
                        CanAddZone = %s,
                        CanAddZoneArea = %s,
                        CanQuickRegister = %s,
                        CanAccessRoleAccess = %s
                    FROM EmployeeRoles er
                    WHERE u.UserId = er.employee_id
                    AND er.company_id = %s
                    AND er.role_id = %s
                """

                update_users_params = [
                    permissions['ShowForgetPassword'],
                    permissions['CanViewEmployees'],
                    permissions['CanRegisterEmployee'],
                    permissions['CanRegisterVisitor'],
                    permissions['CanRegisterCombined'],
                    permissions['CanViewVisitors'],
                    permissions['CanViewUsers'],
                    permissions['CanAccessZoneRequests'],
                    permissions['CanAccessVisitorSettings'],
                    permissions['CanAddCompany'],
                    permissions['CanAddDepartment'],
                    permissions['CanAddDesignation'],
                    permissions['CanAddRole'],
                    permissions['CanAddZone'],
                    permissions['CanAddZoneArea'],
                    permissions['CanQuickRegister'],
                    permissions['CanAccessRoleAccess'],
                    company_id,
                    role_id
                ]

                cur.execute(update_users_query, update_users_params)
                conn.commit()

                if request.content_type == 'application/json':
                    return jsonify({'success': True, 'message': 'Role access and user permissions updated successfully!'})
                flash('Role access and user permissions updated successfully!', 'success')

            return render_template('role_access.html',
                                user_id=user[0],
                                photo_filename=photo_filename,
                                show_forget_password=user[1],
                                can_view_employees=user[2],
                                can_register_employee=user[3],
                                can_register_visitor=user[4],
                                can_register_combined=user[5],
                                can_view_visitors=user[6],
                                can_view_users=user[7],
                                can_access_zone_requests=user[8],
                                can_access_visitor_settings=user[9],
                                can_add_company=user[10],
                                can_add_department=user[11],
                                can_add_designation=user[12],
                                can_add_role=user[13],
                                can_add_zone=user[14],
                                can_add_zone_area=user[15],
                                can_quick_register=user[16],
                                can_access_role_access=user[17],
                                companies=companies,
                                roles=roles)

    except Exception as e:
        logging.error(f'Error managing role access: {e}')
        if request.content_type == 'application/json':
            return jsonify({'error': str(e)}), 500
        flash('An error occurred while managing role access. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        conn.close()

        

@app.route('/api/role_access/get', methods=['GET'])
def get_role_access_api():
    company_id = request.args.get('company_id')
    role_id = request.args.get('role_id')

    if not all([company_id, role_id]):
        return jsonify({'error': 'Missing parameters'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor,
                       CanRegisterCombined, CanViewVisitors,
                       CanViewUsers, CanAccessZoneRequests,
                       CanAccessVisitorSettings, CanAddCompany,
                       CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone,
                       CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM RoleAccess
                WHERE company_id = %s AND role_id = %s
            """, (company_id, role_id))
            
            result = cur.fetchone()
            if result:
                return jsonify({
                    'showForgetPassword': result[0],
                    'canViewEmployees': result[1],
                    'canRegisterEmployee': result[2],
                    'canRegisterVisitor': result[3],
                    'canRegisterCombined': result[4],
                    'canViewVisitors': result[5],
                    'canViewUsers': result[6],
                    'canAccessZoneRequests': result[7],
                    'canAccessVisitorSettings': result[8],
                    'canAddCompany': result[9],
                    'canAddDepartment': result[10],
                    'canAddDesignation': result[11],
                    'canAddRole': result[12],
                    'canAddZone': result[13],
                    'canAddZoneArea': result[14],
                    'canQuickRegister': result[15],
                    'canAccessRoleAccess': result[16]
                })
            return jsonify({})
    except Exception as e:
        logging.error(f'Error fetching role access: {e}')
        return jsonify({'error': 'An error occurred while fetching role access'}), 500
    finally:
        conn.close() 

@app.route('/update_user_settings', methods=['GET', 'POST'])
def update_user_settings():
    user_id = request.form.get('userId') if request.method == 'POST' else request.args.get('userId')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing userId parameter'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500

    try:
        with conn.cursor() as cursor:
            valid_settings = {
                'showForgetPassword': 'ShowForgetPassword',
                'canViewEmployees': 'CanViewEmployees',
                'canRegisterEmployee': 'CanRegisterEmployee',
                'canRegisterVisitor': 'CanRegisterVisitor',
                'canRegisterCombined': 'CanRegisterCombined',
                'canViewVisitors': 'CanViewVisitors',
                'canViewUsers': 'CanViewUsers',
                'canAccessZoneRequests': 'CanAccessZoneRequests',
                'canAccessVisitorSettings': 'CanAccessVisitorSettings',
                'canAddCompany': 'CanAddCompany',
                'canAddDepartment': 'CanAddDepartment',
                'canAddDesignation': 'CanAddDesignation',
                'canAddRole': 'CanAddRole',
                'canAddZone': 'CanAddZone',
                'canAddZoneArea': 'CanAddZoneArea',
                'canQuickRegister': 'CanQuickRegister',
                'canAccessRoleAccess': 'CanAccessRoleAccess'
            }

            if request.method == 'POST':
                # Update logic
                setting = request.form.get('setting')
                value = request.form.get('value') == 'true'

                if not setting:
                    return jsonify({'success': False, 'message': 'Missing setting parameter'}), 400

                if setting not in valid_settings:
                    return jsonify({'success': False, 'message': 'Invalid setting'}), 400

                query = f"UPDATE Users SET {valid_settings[setting]} = %s WHERE UserId = %s"
                cursor.execute(query, (value, user_id))

                if cursor.rowcount == 0:
                    return jsonify({'success': False, 'message': 'User not found or setting not changed'}), 404
                
                conn.commit()
                return jsonify({'success': True, 'message': f'{setting} updated successfully for user {user_id}'})

            elif request.method == 'GET':
                # Retrieval logic
                query = """
                SELECT ShowForgetPassword, CanViewEmployees, CanRegisterEmployee, 
                       CanRegisterVisitor, CanRegisterCombined, CanViewVisitors, 
                       CanViewUsers, CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users WHERE UserId = %s
                """
                cursor.execute(query, (user_id,))
                user_settings = cursor.fetchone()

                if user_settings is None:
                    return jsonify({'success': False, 'message': 'User not found'}), 404

                settings_dict = {
                    'showForgetPassword': user_settings[0],
                    'canViewEmployees': user_settings[1],
                    'canRegisterEmployee': user_settings[2],
                    'canRegisterVisitor': user_settings[3],
                    'canRegisterCombined': user_settings[4],
                    'canViewVisitors': user_settings[5],
                    'canViewUsers': user_settings[6],
                    'canAccessZoneRequests': user_settings[7],
                    'canAccessVisitorSettings': user_settings[8],
                    'canAddCompany': user_settings[9],
                    'canAddDepartment': user_settings[10],
                    'canAddDesignation': user_settings[11],
                    'canAddRole': user_settings[12],
                    'canAddZone': user_settings[13],
                    'canAddZoneArea': user_settings[14],
                    'canQuickRegister': user_settings[15],
                    'canAccessRoleAccess': user_settings[16]
                }

                return jsonify({'success': True, 'settings': settings_dict})

    except Exception as e:
        logging.error(f'Error updating/retrieving user setting: {e}')
        return jsonify({'success': False, 'message': 'An error occurred while processing the request'}), 500

    finally:
        conn.close()

@app.route('/update_company_access', methods=['POST'])
def update_company_access():
    user_id = request.form.get('userId')
    companies = json.loads(request.form.get('companies', '[]'))
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing userId parameter'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with conn.cursor() as cursor:
            # First remove existing company access records
            cursor.execute("DELETE FROM UserCompanyAccess WHERE acessuserid = %s", (user_id,))
            
            # Insert new company access records
            for company in companies:
                cursor.execute(
                    "INSERT INTO UserCompanyAccess (acessuserid, Company) VALUES (%s, %s)",
                    (user_id, company)
                )
            
            conn.commit()
            return jsonify({'success': True, 'message': 'Company access updated successfully'})
    
    except Exception as e:
        conn.rollback()  # Add rollback in case of error
        logging.error(f'Error updating company access: {e}')
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/remove_company_access', methods=['POST'])
def remove_company_access():
    user_id = request.form.get('userId')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing userId parameter'}), 400
    
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM UserCompanyAccess WHERE acessuserid = %s", (user_id,))
            conn.commit()
            return jsonify({'success': True, 'message': 'Company access removed successfully'})
    
    except Exception as e:
        logging.error(f'Error removing company access: {e}')
        return jsonify({'success': False, 'message': 'An error occurred while removing company access'}), 500
    finally:
        conn.close()

        
@app.route('/view_employees')
def view_employees():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))
    
    employee_list = []
    
    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None
            
            # Check if the user has permission to view employees
            if not can_view_employees:
                flash('You do not have permission to view employees.', 'danger')
                return redirect(url_for('dashboard'))
            
            # Get the companies this user has access to
            cur.execute("SELECT Company FROM UserCompanyAccess WHERE acessuserid = %s", (user_id,))
            allowed_company_names = [row[0] for row in cur.fetchall()]
            
            # Convert company names to company IDs
            cur.execute("""
                SELECT CompanyID::text 
                FROM CompanyDetails 
                WHERE CompanyName = ANY(%s)
            """, (allowed_company_names,))
            allowed_company_ids = [row[0] for row in cur.fetchall()]
            
            if not allowed_company_ids:
                flash('You do not have access to any company data.', 'info')
                return render_template('view_employees.html', 
                                    employees=[], 
                                    user_id=user_id,
                                    photo_filename=photo_filename,
                                    show_forget_password=show_forget_password,
                                    can_view_employees=can_view_employees,
                                    can_register_employee=can_register_employee,
                                    can_register_visitor=can_register_visitor,
                                    can_register_combined=can_register_combined,
                                    can_view_visitors=can_view_visitors,
                                    can_view_users=can_view_users,
                                    can_access_zone_requests=can_access_zone_requests,
                                    can_access_visitor_settings=can_access_visitor_settings,
                                    can_add_company=can_add_company,
                                    can_add_department=can_add_department,
                                    can_add_designation=can_add_designation,
                                    can_add_role=can_add_role,
                                    can_add_zone=can_add_zone,
                                    can_add_zone_area=can_add_zone_area,
                                    can_quick_register=can_quick_register,
                                    can_access_role_access=can_access_role_access)
            
            # Get employees only from allowed companies with company details
            cur.execute("""
                SELECT 
                    e.Employee_Id, e.First_Name, e.Last_Name, e.Email, 
                    e.Designation, e.Department, e.PhoneNumber, 
                    e.DateOfBirth, e.DateOfJoining, e.DateOfLeave, 
                    e.Status, e.Address, e.Photo, e.Company, 
                    cd.CompanyName, e.ReportingManager
                FROM Employee e
                JOIN CompanyDetails cd ON e.Company = cd.CompanyID::text
                WHERE e.Company = ANY(%s)
                ORDER BY e.First_Name ASC
            """, (allowed_company_ids,))
            
            employees = cur.fetchall()
            
            # Debug prints
            print("Allowed Company Names:", allowed_company_names)
            print("Allowed Company IDs:", allowed_company_ids)
            print("Number of employees found:", len(employees))
            
            if employees:
                employee_list = [{
                    'Employee_Id': emp[0],
                    'First_Name': emp[1],
                    'Last_Name': emp[2],
                    'Email': emp[3],
                    'Designation': emp[4],
                    'Department': emp[5],
                    'PhoneNumber': emp[6],
                    'DateOfBirth': emp[7],
                    'DateOfJoining': emp[8],
                    'DateOfLeave': emp[9],
                    'Status': emp[10],
                    'Address': emp[11],
                    'Photo': emp[12],
                    'Company': emp[14], 
                    'ReportingManager': emp[15]
                } for emp in employees]
            else:
                flash('No employees found in your accessible companies.', 'info')
    
    except Exception as e:
        logging.error(f'Error in view_employees: {e}')
        flash('An error occurred while fetching employees. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    
    finally:
        conn.close()
    
    return render_template('view_employees.html', 
                         employees=employee_list,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

@app.route('/get_employee_details/<int:employee_id>')
def get_employee_details(employee_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Fetch the full details of the employee
            cur.execute("""
                SELECT 
                    Employee_Id, First_Name, Last_Name, Email, Designation, Department, PhoneNumber, 
                    DateOfBirth, DateOfJoining, DateOfLeave, Status, Address, Photo, Company, ReportingManager
                FROM Employee
                WHERE Employee_Id = %s
            """, (employee_id,))
            employee = cur.fetchone()

            if employee:
                employee_data = {
                    'Employee_Id': employee[0],
                    'First_Name': employee[1],
                    'Last_Name': employee[2],
                    'Email': employee[3],
                    'Designation': employee[4],
                    'Department': employee[5],
                    'PhoneNumber': employee[6],
                    'DateOfBirth': employee[7],
                    'DateOfJoining': employee[8],
                    'DateOfLeave': employee[9],
                    'Status': employee[10],
                    'Address': employee[11],
                    'Photo': employee[12],
                    'Company': employee[13],
                    'ReportingManager': employee[14]
                }
                return jsonify(employee_data)
            else:
                return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        logging.error(f"Error fetching employee details: {e}")
        return jsonify({'error': 'Error fetching employee details'}), 500
    finally:
        conn.close()


@app.route('/update_leave_status/<string:employee_id>', methods=['POST'])
def update_leave_status(employee_id):
    conn = None
    try:
        # Get the current date
        current_date = datetime.now().date()

        # Database connection
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Update the DateOfLeave and Status for the employee
            cur.execute("""
                UPDATE Employee 
                SET DateOfLeave = %s, Status = FALSE
                WHERE Employee_Id = %s
            """, (current_date, employee_id))

            # Commit changes
            conn.commit()

        return jsonify({
            "message": "Leave status updated successfully.",
            "date_of_leave": current_date.isoformat(),
            "status": False
        }), 200

    except Exception as e:
        # Error logging
        print(f"Error updating leave status: {e}")
        return jsonify({"message": f"Error updating leave status: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()

        
@app.route('/edit_employee/<employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('view_employees'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees,
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching user data. Please try again.', 'danger')
        return redirect(url_for('view_employees'))

    if request.method == 'POST':
        # Retrieve updated data from the form
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        designation = request.form.get('designation')
        department = request.form.get('department')
        phone_number = request.form.get('phone_number')
        date_of_birth = request.form.get('date_of_birth')
        date_of_joining = request.form.get('date_of_joining')
        address = request.form.get('address', '')

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE Employee
                    SET First_Name = %s, Last_Name = %s, Email = %s,
                        Designation = %s, Department = %s, PhoneNumber = %s,
                        DateOfBirth = %s, DateOfJoining = %s, Address = %s
                    WHERE Employee_Id = %s
                """, (first_name, last_name, email, designation, department,
                      phone_number, date_of_birth, date_of_joining, address, employee_id))
                conn.commit()
            flash('Employee details updated successfully!', 'success')
            return redirect(url_for('view_employees'))

        except Exception as e:
            logging.error(f'Error updating employee: {e}')
            flash('An error occurred while updating employee details. Please try again.', 'danger')
        finally:
            conn.close()

    # GET request: Fetch current employee data to populate the form
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM Employee WHERE Employee_Id = %s", (employee_id,))
            employee = cur.fetchone()
            if employee:
                return render_template('edit_employee.html', 
                                    employee=employee,
                                    user_id=user_id,
                                    show_forget_password=show_forget_password,
                                    can_view_employees=can_view_employees,
                                    can_register_employee=can_register_employee,
                                    can_register_visitor=can_register_visitor,
                                    can_register_combined=can_register_combined,
                                    can_view_visitors=can_view_visitors,
                                    can_view_users=can_view_users,
                                    can_access_zone_requests=can_access_zone_requests,
                                    can_access_visitor_settings=can_access_visitor_settings,
                                    can_add_company=can_add_company,
                                    can_add_department=can_add_department,
                                    can_add_designation=can_add_designation,
                                    can_add_role=can_add_role,
                                    can_add_zone=can_add_zone,
                                    can_add_zone_area=can_add_zone_area,
                                    can_quick_register=can_quick_register,
                                    can_access_role_access=can_access_role_access)
            else:
                flash('Employee not found.', 'danger')
                return redirect(url_for('view_employees'))

    except Exception as e:
        logging.error(f'Error fetching employee data: {e}')
        flash('An error occurred while fetching employee details. Please try again.', 'danger')
        return redirect(url_for('view_employees'))

@app.route('/register_visitor', methods=['GET', 'POST'])
def register_visitor():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch zones with more detailed information
            cur.execute("""
                SELECT 
                    CompanyZoneID, 
                    ZoneName, 
                    CreatedBy, 
                    CreatedAt
                FROM CompanyZones
            """)
            zones = cur.fetchall()

            # Fetch visit areas with comprehensive zone and company information
            cur.execute("""
                SELECT 
                    cza.VisitAreaName, 
                    cd.CompanyName, 
                    cz.ZoneName,
                    cz.CompanyZoneID
                FROM CompanyZoneAreas cza
                JOIN CompanyZones cz ON cza.CompanyZoneID = cz.CompanyZoneID
                JOIN CompanyDetails cd ON cza.CompanyID = cd.CompanyID
            """)
            visit_areas = cur.fetchall()

            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Get logged-in employee's company
            cur.execute("""
                SELECT Company FROM Employee 
                WHERE Employee_Id = %s
            """, (user_id,))
            result = cur.fetchone()
            employee_company = result[0] if result else None

            # Fetch all companies for dropdown with their locations
            cur.execute("""
                SELECT 
                    cd.CompanyID, 
                    cd.CompanyName,
                    COALESCE(cd.Address || ', ' || cd.CityLocation || ', ' || cd.StateName, '') AS full_address
                FROM CompanyDetails cd
            """)
            companies = cur.fetchall()

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    today = date.today()
    
    if request.method == 'POST':
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Get form data for email and phone
                email = request.form.get('email')
                phone = request.form.get('phone')

                # Check for existing visitor with active check-in or pending status
                cur.execute("""
                    SELECT v.VisitorId, vvs.VisitStatus, vvs.InTime, vvs.OutTime, vvs.VisitDate
                    FROM Visitor v
                    JOIN VisitorAppointment va ON v.VisitorId = va.VisitorId
                    JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
                    WHERE (v.Email = %s OR v.Phone = %s)
                    AND (
                        (vvs.InTime IS NOT NULL AND vvs.OutTime IS NULL)
                        OR vvs.VisitStatus = 'Pending'
                    )
                    ORDER BY vvs.VisitDate DESC
                    LIMIT 1
                """, (email, phone))
                
                existing_visit = cur.fetchone()
                
                if existing_visit:
                    if existing_visit[2] and not existing_visit[3]:  # Has check-in but no check-out
                        flash('Cannot register visitor. They are currently checked in at another location.', 'danger')
                        return redirect(url_for('register_visitor'))
                    elif existing_visit[1] == 'Pending' and existing_visit[4] >= today:
                        flash('Cannot register visitor. They have a pending visit.', 'danger')
                        return redirect(url_for('register_visitor'))

                # Get selected company details
                selected_company_id = request.form.get('organization_name')
                
                # Try to get company details using the raw input
                cur.execute("""
                    SELECT 
                        CompanyID,
                        CompanyName,
                        COALESCE(Address || ', ' || CityLocation || ', ' || StateName, '') AS full_address
                    FROM CompanyDetails 
                    WHERE CompanyID::text = %s OR CompanyName = %s
                """, (selected_company_id, selected_company_id))
                
                company_details = cur.fetchone()
                
                if company_details:
                    company_id = company_details[0]
                    company_name = company_details[1]
                    company_location = company_details[2]
                else:
                    company_name = selected_company_id
                    company_location = 'N/A'
                    company_id = None

                # Extract form data
                data = {
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'email': email,
                    'phone': phone,
                    'visit_date': request.form.get('visit_date'),
                    'visit_purpose': request.form.get('visit_purpose'),
                    'visit_area': request.form.get('visit_area'),
                    'host_name': request.form.get('host_name'),
                    'visitor_organization': request.form.get('visitor_organization'),
                    'visitor_location': request.form.get('visitor_location'),
                    'organization_name': company_name,
                    'organization_location': company_location,
                    'zone_select': request.form.get('zone_select')
                }

                # Validate required fields
                required_fields = ['first_name', 'last_name', 'email', 'phone', 'visit_date', 'organization_name']
                
                for field in required_fields:
                    if not data[field]:
                        flash(f'{field.replace("_", " ").title()} is required.', 'danger')
                        return redirect(url_for('register_visitor'))

                # Determine zone status and handling
                if data['visit_area']:
                    zone_status = 'pending'
                elif data['zone_select']:
                    zone_status = 'Green Zone' if data['zone_select'] == 'Green Zone' else 'Red Zone'
                else:
                    zone_status = 'Green Zone'

                created_at = datetime.now()

                # Convert visit_date to date object with validation
                try:
                    visit_date = datetime.strptime(data['visit_date'], '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                    return redirect(url_for('register_visitor'))

                # Determine visitor status
                new_status = 'Pending' if visit_date >= today else 'No Visit'

                # Check for existing visitor
                cur.execute("""
                    SELECT v.VisitorId, v.FirstName, v.LastName 
                    FROM Visitor v
                    WHERE v.Email = %s OR v.Phone = %s
                """, (data['email'], data['phone']))
                existing_visitor = cur.fetchone()

                if existing_visitor:
                    visitor_id = existing_visitor[0]
                else:
                    # Create new visitor
                    cur.execute("""
                        INSERT INTO Visitor (
                            FirstName, LastName, Email, Phone, 
                            HostName, CreatedBy, CreatedAt, VisitDate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING VisitorId
                    """, (
                        data['first_name'], data['last_name'], data['email'], 
                        data['phone'], data['host_name'], user_id, created_at, visit_date
                    ))
                    visitor_id = cur.fetchone()[0]

                # Create new appointment
                cur.execute("""
                    INSERT INTO VisitorAppointment (
                        VisitorId, AppointmentDate, AppointmentLocation,
                        CreatedAt, CreatedBy
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING AppointmentId
                """, (
                    visitor_id, visit_date, data['organization_location'],
                    created_at, user_id
                ))
                appointment_id = cur.fetchone()[0]

                # Create new visit status
                cur.execute("""
                    INSERT INTO VisitorVisitStatus (
                        VisitorId, VisitStatus, VisitPurpose, 
                        CreatedBy, CreatedAt, VisitDate,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, new_status, data['visit_purpose'],
                    user_id, created_at, visit_date, appointment_id
                ))

                # Create new organization status with the correct location
                cur.execute("""
                    INSERT INTO VisitorOrganizationVisitStatus (
                        VisitorId, VisitorFromOrganization, VisitorFromLocation,
                        VisitInOrganization, VisitInLocation, CreatedBy, CreatedAt,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, data['visitor_organization'], data['visitor_location'],
                    data['organization_name'], data['organization_location'], user_id, created_at,
                    appointment_id
                ))

                # Create new zone status
                if zone_status == 'pending':
                    cur.execute("""
                        INSERT INTO Visitor_Zone_Status (
                            zone_visitor_id, zone_requester_user_id, 
                            zone_visit_area, zone_visit_purpose, 
                            zone_status, zone_request_time,
                            AppointmentId, company_zone_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        visitor_id, user_id, 
                        data['visit_area'] or data['zone_select'], 
                        data['visit_purpose'], 
                        zone_status, 
                        created_at,
                        appointment_id, 
                        data.get('zone_select') or data.get('visit_area')
                    ))
                elif zone_status != 'Green Zone':
                    cur.execute("""
                        INSERT INTO Visitor_Zone_Status (
                            zone_visitor_id, zone_requester_user_id, 
                            zone_visit_area, zone_visit_purpose, 
                            zone_status, zone_request_time,
                            AppointmentId, company_zone_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        visitor_id, user_id, 
                        data['zone_select'] or data['visit_area'],
                        data['visit_purpose'], 
                        zone_status, 
                        created_at,
                        appointment_id,
                        data.get('zone_select')
                    ))

                conn.commit()
                flash('Visitor registered successfully!', 'success')
                return redirect(url_for('dashboard'))

        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f'Error registering visitor: {e}', exc_info=True)
            flash(f'An error occurred while registering the visitor: {str(e)}', 'danger')
            return redirect(url_for('register_visitor'))
        finally:
            if conn:
                conn.close()

    return render_template('register_visitor.html', 
                         employee_company=employee_company,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         companies=companies,
                         zones=zones,
                         visit_areas=visit_areas)

@app.route('/quick_register_visitor', methods=['GET', 'POST'])
def quick_register_visitor():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Get logged-in employee's company with company name from CompanyDetails
            cur.execute("""
                SELECT cd.CompanyName, cd.Address || ', ' || cd.CityLocation || ', ' || cd.StateName,
                       e.Company
                FROM Employee e
                JOIN CompanyDetails cd ON e.Company = CAST(cd.CompanyID AS VARCHAR)
                WHERE e.Employee_Id = %s
            """, (user_id,))
            result = cur.fetchone()
            employee_company = result[0] if result else None
            employee_location = result[1] if result else None
            employee_company_id = result[2] if result else None

            if not employee_company:
                flash('Company information not found. Please update your profile.', 'warning')
                return redirect(url_for('dashboard'))

            # Fetch zones with more detailed information
            cur.execute("""
                SELECT 
                    CompanyZoneID, 
                    ZoneName, 
                    CreatedBy, 
                    CreatedAt
                FROM CompanyZones
            """)
            zones = cur.fetchall()

            # Create a dictionary to look up zone names
            zone_names = {str(zone[0]): zone[1] for zone in zones}

            # Fetch visit areas with comprehensive zone and company information
            cur.execute("""
                SELECT 
                    cza.VisitAreaName, 
                    cd.CompanyName, 
                    cz.ZoneName,
                    cz.CompanyZoneID
                FROM CompanyZoneAreas cza
                JOIN CompanyZones cz ON cza.CompanyZoneID = cz.CompanyZoneID
                JOIN CompanyDetails cd ON cza.CompanyID = cd.CompanyID
            """)
            visit_areas = cur.fetchall()

            # Create a dictionary to look up area zone names
            area_zone_names = {area[0]: area[2] for area in visit_areas}

            # Fetch user settings with additional permissions
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            user_id = user[0]
            show_forget_password = user[1]
            can_view_employees = user[2]
            can_register_employee = user[3]
            can_register_visitor = user[4]
            can_register_combined = user[5]
            can_view_visitors = user[6]
            can_view_users = user[7]
            can_access_zone_requests = user[8]
            can_access_visitor_settings = user[9]
            can_add_company = user[10]
            can_add_department = user[11]
            can_add_designation = user[12]
            can_add_role = user[13]
            can_add_zone = user[14]
            can_add_zone_area = user[15]
            can_quick_register = user[16]
            can_access_role_access = user[17]

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Fetch all companies
            cur.execute("""
                SELECT CompanyID, CompanyName, 
                       COALESCE(Address || ', ' || CityLocation || ', ' || StateName, '') AS full_address 
                FROM CompanyDetails
            """)
            companies = cur.fetchall()

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    today = date.today()

    if request.method == 'POST':
        # Extract form data
        data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'visit_date': request.form.get('visit_date'),
            'visit_purpose': request.form.get('visit_purpose'),
            'visit_area': request.form.get('visit_area'),
            'host_name': request.form.get('host_name'),
            'visitor_organization': '',  # Empty for quick register
            'visitor_location': '',      # Empty for quick register
            'organization_name': request.form.get('organization_name', employee_company),
            'organization_location': employee_location or 'N/A',
            'zone_select': request.form.get('zone_select')
        }

        # Get the zone name based on selection
        selected_zone_name = None
        if data['visit_area']:
            # If visit_area is selected, get its corresponding zone name
            selected_zone_name = area_zone_names.get(data['visit_area'])
        elif data['zone_select']:
            # If zone is directly selected, use that name
            selected_zone_name = zone_names.get(data['zone_select'])

        # Validate required fields
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'visit_date', 'host_name']
        
        for field in required_fields:
            if not data[field]:
                flash(f'{field.replace("_", " ").title()} is required.', 'danger')
                return redirect(url_for('quick_register_visitor'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('dashboard'))

        try:
            with conn.cursor() as cur:
                # Check for existing visitor with active check-in or pending status
                cur.execute("""
                    SELECT v.VisitorId, vvs.VisitStatus, vvs.InTime, vvs.OutTime, vvs.VisitDate
                    FROM Visitor v
                    JOIN VisitorAppointment va ON v.VisitorId = va.VisitorId
                    JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
                    WHERE (v.Email = %s OR v.Phone = %s)
                    AND (
                        (vvs.InTime IS NOT NULL AND vvs.OutTime IS NULL)
                        OR vvs.VisitStatus = 'Pending'
                    )
                    ORDER BY vvs.VisitDate DESC
                    LIMIT 1
                """, (data['email'], data['phone']))
                
                existing_visit = cur.fetchone()
                
                if existing_visit:
                    if existing_visit[2] and not existing_visit[3]:  # Has check-in but no check-out
                        flash('Cannot register visitor. They are currently checked in at another location.', 'danger')
                        return redirect(url_for('quick_register_visitor'))
                    elif existing_visit[1] == 'Pending' and existing_visit[4] >= today:
                        flash('Cannot register visitor. They have a pending visit.', 'danger')
                        return redirect(url_for('quick_register_visitor'))

                # Convert visit_date to date object
                try:
                    visit_date = datetime.strptime(data['visit_date'], '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
                    return redirect(url_for('quick_register_visitor'))

                # Determine visitor status
                new_status = 'Pending' if visit_date >= today else 'No Visit'

                # Determine zone status
                if data['visit_area']:
                    zone_status = 'pending'
                elif data['zone_select']:
                    zone_status = 'Green Zone' if data['zone_select'] == 'Green Zone' else 'Red Zone'
                else:
                    zone_status = 'Green Zone'

                created_at = datetime.now()

                # Check for existing visitor
                cur.execute("""
                    SELECT v.VisitorId, v.FirstName, v.LastName 
                    FROM Visitor v
                    WHERE v.Email = %s OR v.Phone = %s
                """, (data['email'], data['phone']))
                existing_visitor = cur.fetchone()

                if existing_visitor:
                    visitor_id = existing_visitor[0]
                else:
                    # Create new visitor - without Organization field
                    cur.execute("""
                        INSERT INTO Visitor (
                            FirstName, LastName, Email, Phone, 
                            HostName, CreatedBy, CreatedAt, VisitDate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING VisitorId
                    """, (
                        data['first_name'], data['last_name'], data['email'], 
                        data['phone'], data['host_name'], user_id, created_at, visit_date
                    ))
                    visitor_id = cur.fetchone()[0]

                # Create new appointment
                cur.execute("""
                    INSERT INTO VisitorAppointment (
                        VisitorId, AppointmentDate, AppointmentLocation,
                        CreatedAt, CreatedBy
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING AppointmentId
                """, (
                    visitor_id, visit_date, data['organization_location'],
                    created_at, user_id
                ))
                appointment_id = cur.fetchone()[0]

                # Create new visit status
                cur.execute("""
                    INSERT INTO VisitorVisitStatus (
                        VisitorId, VisitStatus, VisitPurpose, 
                        CreatedBy, CreatedAt, VisitDate,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, new_status, data['visit_purpose'],
                    user_id, created_at, visit_date, appointment_id
                ))

                # Create new organization status
                cur.execute("""
                    INSERT INTO VisitorOrganizationVisitStatus (
                        VisitorId, VisitorFromOrganization, VisitorFromLocation,
                        VisitInOrganization, VisitInLocation, CreatedBy, CreatedAt,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, data['visitor_organization'], data['visitor_location'],
                    data['organization_name'], data['organization_location'], 
                    user_id, created_at, appointment_id
                ))

                # Create new zone status based on conditions
                if zone_status == 'pending':
                    cur.execute("""
                        INSERT INTO Visitor_Zone_Status (
                            zone_visitor_id, zone_requester_user_id, 
                            zone_visit_area, zone_visit_purpose, 
                            zone_status, zone_request_time,
                            AppointmentId, company_zone_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        visitor_id, user_id, 
                        data['visit_area'], 
                        data['visit_purpose'], 
                        zone_status, created_at,
                        appointment_id, 
                        selected_zone_name  # Store zone name instead of ID
                    ))
                elif zone_status != 'Green Zone':
                    cur.execute("""
                        INSERT INTO Visitor_Zone_Status (
                            zone_visitor_id, zone_requester_user_id, 
                            zone_visit_area, zone_visit_purpose, 
                            zone_status, zone_request_time,
                            AppointmentId, company_zone_id
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        visitor_id, user_id, 
                        data['zone_select'],
                        data['visit_purpose'], 
                        zone_status, created_at,
                        appointment_id,
                        selected_zone_name  # Store zone name instead of ID
                    ))

                conn.commit()
                flash('Visitor registered successfully!', 'success')
                return redirect(url_for('dashboard'))

        except Exception as e:
            if conn:
                conn.rollback()
            logging.error(f'Error registering visitor: {e}', exc_info=True)
            flash(f'An error occurred while registering the visitor: {str(e)}', 'danger')
            return redirect(url_for('quick_register_visitor'))
        finally:
            if conn:
                conn.close()

    return render_template('quick_register_visitor.html', 
                         employee_company=employee_company,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         companies=companies,
                         zones=zones,
                         visit_areas=visit_areas)


@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    # Ensure user is authenticated and user ID is available
    user_id = session.get('user_id')
    if not user_id:
        flash('You need to be logged in to add a company.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Get logged-in employee's company
            cur.execute("""
                SELECT Company FROM Employee 
                WHERE Employee_Id = %s
            """, (user_id,))
            result = cur.fetchone()
            employee_company = result[0] if result else None

            # Fetch all companies for displaying in the dropdown
            cur.execute("""
                SELECT CompanyID, CompanyName, 
                       COALESCE(Address || ', ' || CityLocation || ', ' || StateName, '') AS full_address 
                FROM CompanyDetails
            """)
            companies = cur.fetchall()

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    # Handle form submission for adding a new company
    if request.method == 'POST':
        # Retrieve data from the form
        company_name = request.form.get('companyName')
        address = request.form.get('address')
        city_location = request.form.get('cityLocation')
        state_name = request.form.get('stateName')
        country = request.form.get('country')
        zip_code = request.form.get('zipCode')

        # Validate required fields
        if not all([company_name, address, city_location, state_name, country, zip_code]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_company'))

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('add_company'))

        try:
            with conn.cursor() as cur:
                # Check if the company name already exists
                cur.execute("SELECT COUNT(*) FROM CompanyDetails WHERE CompanyName = %s", (company_name,))
                company_exists = cur.fetchone()[0]

                if company_exists > 0:
                    flash('Company name already exists. Please choose a different name.', 'danger')
                    return redirect(url_for('add_company'))

                # Insert the new company into the database with the current user's ID as 'CreatedBy'
                cur.execute("""
                    INSERT INTO CompanyDetails (CompanyName, Address, CityLocation, StateName, Country, ZipCode, CreatedBy, CreatedAt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (company_name, address, city_location, state_name, country, zip_code, user_id, datetime.now()))
                conn.commit()
                flash('Company added successfully!', 'success')
                return redirect(url_for('add_company'))

        except Exception as e:
            logging.error(f'Error adding company: {e}', exc_info=True)
            flash('An error occurred while adding the company. Please try again.', 'danger')
            return redirect(url_for('add_company'))
        finally:
            conn.close()

    # Fetch all companies for displaying
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM CompanyDetails")
                companies = cur.fetchall()
        except Exception as e:
            logging.error(f'Error fetching companies: {e}', exc_info=True)
            companies = []
        finally:
            conn.close()
    else:
        companies = []

    # Render the form for adding a company and display the list of companies
    return render_template('add_company.html', 
                         employee_company=employee_company,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         companies=companies)


@app.route('/add_zone_area', methods=['GET', 'POST'])
def add_zone_area():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT CompanyID, CompanyName FROM CompanyDetails")
            companies = cur.fetchall()
            
            cur.execute("SELECT CompanyZoneID, ZoneName FROM CompanyZones")
            zones = cur.fetchall()

            if request.method == 'POST':
                company_id = request.form.get('companyId')
                company_zone_id = request.form.get('companyZoneId')
                visit_area_name = request.form.get('visitAreaName')

                if not all([company_id, company_zone_id, visit_area_name]):
                    return jsonify({'success': False, 'message': 'All fields are required'}), 400

                # Check for duplicates
                cur.execute("""
                    SELECT 1 FROM CompanyZoneAreas 
                    WHERE CompanyID = %s AND CompanyZoneID = %s AND VisitAreaName = %s
                """, (company_id, company_zone_id, visit_area_name))
                
                if cur.fetchone():
                    return jsonify({
                        'success': False, 
                        'message': 'Zone area already exists'
                    }), 400

                # Insert new zone area
                cur.execute("""
                    INSERT INTO CompanyZoneAreas (CompanyZoneID, CompanyID, VisitAreaName, CreatedBy)
                    VALUES (%s, %s, %s, %s)
                    RETURNING VisitAreaName
                """, (company_zone_id, company_id, visit_area_name, user_id))
                
                new_area = cur.fetchone()
                conn.commit()

                return jsonify({
                    'success': True,
                    'message': 'Zone area added successfully',
                    'data': {
                        'visitAreaName': new_area[0],
                        'companyId': company_id,
                        'zoneId': company_zone_id
                    }
                })

            # Fetch user permissions and settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404

            return render_template('add_zone_area.html',
                                companies=companies,
                                zones=zones,
                                **{k: v for k, v in zip([
                                    'show_forget_password', 'can_view_employees',
                                    'can_register_employee', 'can_register_visitor',
                                    'can_register_combined', 'can_view_visitors',
                                    'can_view_users', 'can_access_zone_requests',
                                    'can_access_visitor_settings', 'can_add_company',
                                    'can_add_department', 'can_add_designation',
                                    'can_add_role', 'can_add_zone',
                                    'can_add_zone_area', 'can_quick_register',
                                    'can_access_role_access'
                                ], user[1:])})

    except Exception as e:
        logging.error(f'Error in add_zone_area: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/edit_zone_area', methods=['POST'])
def edit_zone_area():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    try:
        company_id = request.form.get('companyId')
        company_zone_id = request.form.get('companyZoneId')
        current_zone_area = request.form.get('currentZoneArea')
        new_zone_area_name = request.form.get('newVisitAreaName')

        if not all([company_id, company_zone_id, current_zone_area, new_zone_area_name]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400

        conn = get_db_connection()
        with conn.cursor() as cur:
            # Check for duplicates
            cur.execute("""
                SELECT 1 FROM CompanyZoneAreas 
                WHERE CompanyID = %s AND CompanyZoneID = %s AND VisitAreaName = %s
                AND VisitAreaName != %s
            """, (company_id, company_zone_id, new_zone_area_name, current_zone_area))
            
            if cur.fetchone():
                return jsonify({
                    'success': False,
                    'message': 'Zone area with this name already exists'
                }), 400

            # Update zone area
            cur.execute("""
                UPDATE CompanyZoneAreas 
                SET VisitAreaName = %s, UpdatedBy = %s, UpdatedAt = CURRENT_TIMESTAMP
                WHERE CompanyID = %s AND CompanyZoneID = %s AND VisitAreaName = %s
                RETURNING VisitAreaName
            """, (new_zone_area_name, user_id, company_id, company_zone_id, current_zone_area))
            
            updated_area = cur.fetchone()
            if not updated_area:
                return jsonify({
                    'success': False,
                    'message': 'Zone area not found'
                }), 404

            conn.commit()
            return jsonify({
                'success': True,
                'message': 'Zone area updated successfully',
                'data': {
                    'visitAreaName': updated_area[0],
                    'companyId': company_id,
                    'zoneId': company_zone_id
                }
            })

    except Exception as e:
        logging.error(f'Error in edit_zone_area: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/get_zone_areas')
def get_zone_areas():
    company_id = request.args.get('company_id')
    zone_id = request.args.get('zone_id')
    
    if not all([company_id, zone_id]):
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT VisitAreaName 
                FROM CompanyZoneAreas 
                WHERE CompanyID = %s AND CompanyZoneID = %s
                ORDER BY VisitAreaName
            """, (company_id, zone_id))
            zone_areas = cur.fetchall()
            
            return jsonify({
                'success': True,
                'data': zone_areas
            })
    except Exception as e:
        logging.error(f'Error in get_zone_areas: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/add_zone', methods=['GET', 'POST'])
def add_zone():
    user_id = session.get('user_id')
    if not user_id:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'You need to be logged in to add a zone.'})
        flash('You need to be logged in to add a zone.', 'danger')
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'Database connection error.'})
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                if request.method == 'POST':
                    return jsonify({'success': False, 'message': 'User not found.'})
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Unpack user permissions
            (user_id, show_forget_password, can_view_employees,
             can_register_employee, can_register_visitor,
             can_register_combined, can_view_visitors, can_view_users,
             can_access_zone_requests, can_access_visitor_settings,
             can_add_company, can_add_department, can_add_designation,
             can_add_role, can_add_zone, can_add_zone_area,
             can_quick_register, can_access_role_access) = user

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Get employee's company
            cur.execute("SELECT Company FROM Employee WHERE Employee_Id = %s", (user_id,))
            result = cur.fetchone()
            employee_company = result[0] if result else None

            # Fetch existing zones
            cur.execute("SELECT CompanyZoneID, ZoneName FROM CompanyZones ORDER BY ZoneName")
            zones = cur.fetchall()

            if request.method == 'POST':
                zone_name = request.form.get('zoneName')
                
                if not zone_name:
                    return jsonify({'success': False, 'message': 'Zone name is required.'})

                # Check for duplicate zone
                cur.execute("SELECT 1 FROM CompanyZones WHERE ZoneName = %s", (zone_name,))
                if cur.fetchone():
                    return jsonify({
                        'success': False,
                        'message': 'This zone already exists.'
                    })

                # Insert the new zone
                cur.execute("""
                    INSERT INTO CompanyZones (ZoneName, CreatedBy)
                    VALUES (%s, %s)
                    RETURNING CompanyZoneID, ZoneName
                """, (zone_name, user_id))
                new_zone = cur.fetchone()
                conn.commit()

                return jsonify({
                    'success': True,
                    'message': 'Zone added successfully!',
                    'zone': {
                        'zone_id': new_zone[0],
                        'zone_name': new_zone[1]
                    }
                })

    except Exception as e:
        logging.error(f'Error in add_zone: {e}')
        if request.method == 'POST':
            return jsonify({'success': False, 'message': 'An error occurred. Please try again.'})
        flash('An error occurred. Please try again.', 'danger')
        return redirect(url_for('add_zone'))
    finally:
        conn.close()

    return render_template('add_zone.html',
                         employee_company=employee_company,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         zones=zones)

@app.route('/edit_zone', methods=['POST'])
def edit_zone():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'You need to be logged in to edit a zone.'})

    try:
        data = request.json
        zone_id = data.get('zoneId')
        new_zone_name = data.get('zoneName')

        if not zone_id or not new_zone_name:
            return jsonify({'success': False, 'message': 'Zone ID and name are required.'})

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'message': 'Database connection error.'})

        with conn.cursor() as cur:
            # Check if the zone name already exists (excluding current zone)
            cur.execute("""
                SELECT 1 FROM CompanyZones 
                WHERE ZoneName = %s AND CompanyZoneID != %s
            """, (new_zone_name, zone_id))
            
            if cur.fetchone():
                return jsonify({
                    'success': False,
                    'message': 'Zone name already exists. Please choose a different name.'
                })

            # Update the zone name
            cur.execute("""
                UPDATE CompanyZones 
                SET ZoneName = %s, UpdatedBy = %s, UpdatedAt = %s
                WHERE CompanyZoneID = %s
            """, (new_zone_name, user_id, datetime.now(), zone_id))
            conn.commit()

            return jsonify({'success': True, 'message': 'Zone updated successfully!'})

    except Exception as e:
        logging.error(f'Error in edit_zone: {e}')
        return jsonify({'success': False, 'message': 'An error occurred while updating the zone.'})
    finally:
        if conn:
            conn.close()

@app.route('/get_zones', methods=['GET'])
def get_zones():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Database connection error'}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT CompanyZoneID, ZoneName
                FROM CompanyZones
                ORDER BY ZoneName
            """)
            zones = cur.fetchall()
            return jsonify([{'zone_id': zone[0], 'zone_name': zone[1]} for zone in zones])

    except Exception as e:
        logging.error(f'Error fetching zones: {e}')
        return jsonify({'error': 'An error occurred while fetching zones'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/view_visitors')
def view_visitors():
    user_id = session.get('user_id')

    # Check if the user is logged in
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Get logged-in employee's company
            cur.execute("""
                SELECT Company FROM Employee 
                WHERE Employee_Id = %s
            """, (user_id,))
            result = cur.fetchone()
            employee_company = result[0] if result else None

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    # Fetch visitor list
    visitor_list = []
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Update visit status for past pending visits
            cur.execute("""
                UPDATE VisitorVisitStatus
                SET VisitStatus = 'No Visit'
                WHERE VisitDate < CURRENT_DATE 
                AND VisitStatus = 'Pending'
            """)
            conn.commit()

            base_query =  """
    SELECT 
        v.VisitorId,
        v.FirstName,
        v.LastName,
        v.Email,
        v.Phone,
        v.HostName,
        vvs.VisitDate,
        vvs.VisitPurpose,
        vvs.VisitStatus,
        vvs.InTimePhoto,
        vvs.OutTimePhoto,
        vvs.InTime,
        vvs.OutTime,
        vvs.CreatedAt as visit_created_at,
        vovs.VisitorFromOrganization,
        vovs.VisitorFromLocation,
        vovs.VisitInOrganization,
        vovs.VisitInLocation,
        COALESCE(vzs.zone_status, 'green zone') as zone_status,
        va.AppointmentId,
        va.AppointmentDate,
        va.AppointmentLocation,
        vh.updateid as last_update_id,
        vh.update_reason as last_update_reason
    FROM VisitorAppointment va
    INNER JOIN Visitor v ON va.VisitorId = v.VisitorId
    INNER JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
    INNER JOIN VisitorOrganizationVisitStatus vovs ON va.AppointmentId = vovs.AppointmentId
    LEFT JOIN Visitor_Zone_Status vzs ON va.AppointmentId = vzs.AppointmentId
    LEFT JOIN VisitorUpdateHistory vh ON va.AppointmentId = vh.AppointmentId
    ORDER BY va.AppointmentDate DESC, va.CreatedAt DESC
"""
            
            cur.execute(base_query)
            visitors = cur.fetchall()

            if visitors:
                visitor_list = [{
        'VisitorId': visitor[0],
        'FirstName': visitor[1],
        'LastName': visitor[2],
        'Email': visitor[3],
        'Phone': visitor[4],
        'HostName': visitor[5],
        'VisitDate': visitor[6],
        'VisitPurpose': visitor[7],
        'VisitorStatus': visitor[8],
        'VisitorPhoto': visitor[9],
        'OutTimePhoto': visitor[10],
        'CheckInTime': visitor[11],
        'CheckOutTime': visitor[12],
        'CreatedAt': visitor[13],
        'VisitorOrganization': visitor[14],
        'VisitorLocation': visitor[15],
        'OrganizationName': visitor[16],
        'OrganizationLocation': visitor[17],
        'ZoneStatus': visitor[18],
        'AppointmentId': visitor[19],
        'AppointmentDate': visitor[20],
        'AppointmentLocation': visitor[21],
        'LastUpdateId': visitor[22],
        'LastUpdateReason': visitor[23]
    } for visitor in visitors]

    except Exception as e:
        logging.error(f'Error fetching visitors: {e}')
        flash('An error occurred while fetching visitors. Please try again.', 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('view_visitors.html', 
                         visitors=visitor_list,
                         employee_company=employee_company,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

@app.route('/view_model_visitor/<int:visitor_id>/<int:appointment_id>', methods=['GET'])
def view_model_visitor(visitor_id, appointment_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Extract user settings
            user_id, show_forget_password, can_view_employees, can_register_employee, \
            can_register_visitor, can_register_combined, can_view_visitors, \
            can_view_users, can_access_zone_requests, can_access_visitor_settings, \
            can_add_company, can_add_department, can_add_designation, can_add_role, \
            can_add_zone, can_add_zone_area, can_quick_register, can_access_role_access = user

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

            # Updated query to fetch specific appointment details
            cur.execute("""
                SELECT 
                    v.VisitorId,
                    v.FirstName,
                    v.LastName,
                    v.Email,
                    v.Phone,
                    v.HostName,
                    vvs.VisitDate,
                    vvs.VisitPurpose,
                    vvs.VisitStatus as VisitorStatus,
                    vvs.InTimePhoto as VisitorPhoto,
                    vvs.OutTimePhoto,
                    vvs.InTime as CheckInTime,
                    vvs.OutTime as CheckOutTime,
                    vovs.VisitorFromOrganization,
                    vovs.VisitorFromLocation,
                    vovs.VisitInOrganization as OrganizationName,
                    vovs.VisitInLocation as OrganizationLocation,
                    COALESCE(vzs.zone_status, 'green zone') as ZoneStatus,
                    va.AppointmentId,
                    va.AppointmentDate,
                    va.AppointmentLocation,
                    vh.updateid as LastUpdateId,
                    vh.update_reason as LastUpdateReason,
                    va.CreatedAt
                FROM VisitorAppointment va
                INNER JOIN Visitor v ON va.VisitorId = v.VisitorId
                INNER JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
                INNER JOIN VisitorOrganizationVisitStatus vovs ON va.AppointmentId = vovs.AppointmentId
                LEFT JOIN Visitor_Zone_Status vzs ON va.AppointmentId = vzs.AppointmentId
                LEFT JOIN VisitorUpdateHistory vh ON va.AppointmentId = vh.AppointmentId
                WHERE v.VisitorId = %s AND va.AppointmentId = %s
            """, (visitor_id, appointment_id))
            
            result = cur.fetchone()

            if result:
                visitor_data = {
                    'VisitorId': result[0],
                    'FirstName': result[1],
                    'LastName': result[2],
                    'Email': result[3],
                    'Phone': result[4],
                    'HostName': result[5],
                    'VisitDate': result[6],
                    'VisitPurpose': result[7],
                    'VisitorStatus': result[8],
                    'VisitorPhoto': result[9],
                    'OutTimePhoto': result[10],
                    'CheckInTime': result[11],
                    'CheckOutTime': result[12],
                    'VisitorOrganization': result[13],
                    'VisitorLocation': result[14],
                    'OrganizationName': result[15],
                    'OrganizationLocation': result[16],
                    'ZoneStatus': result[17],
                    'AppointmentId': result[18],
                    'AppointmentDate': result[19],
                    'AppointmentLocation': result[20],
                    'LastUpdateId': result[21],
                    'LastUpdateReason': result[22],
                    'CreatedAt': result[23]
                }
            else:
                flash('Visitor appointment not found.', 'danger')
                return redirect(url_for('view_visitors'))

    except Exception as e:
        logging.error(f'Error fetching visitor details: {e}')
        flash('An error occurred while fetching visitor details. Please try again.', 'danger')
        return redirect(url_for('view_visitors'))
    finally:
        if conn:
            conn.close()

    return render_template('view_model_visitor.html', 
                         visitor=visitor_data,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

@app.route('/edit_visitor/<int:visitor_id>', methods=['GET', 'POST'])
@app.route('/edit_visitor', methods=['GET', 'POST'])
def edit_visitor(visitor_id=None):
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in'}), 401

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'message': 'Database connection error. Please try again later.'}), 500

    visitor = None
    try:
        with conn.cursor() as cur:
            # Fetch user permissions
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if not user:
                return jsonify({'success': False, 'message': 'User not found'}), 404

            # Extract all permissions
            user_id, show_forget_password, can_view_employees, can_register_employee, \
            can_register_visitor, can_register_combined, can_view_visitors, \
            can_view_users, can_access_zone_requests, can_access_visitor_settings, \
            can_add_company, can_add_department, can_add_designation, can_add_role, \
            can_add_zone, can_add_zone_area, can_quick_register, can_access_role_access = user

            # Check if we're searching by email
            email = request.args.get('email')
            if email and not visitor_id:
                cur.execute("""
                    SELECT v.VisitorId, v.FirstName, v.LastName, v.Email, v.Phone,
                           vovs.VisitorFromOrganization, vovs.VisitorFromLocation
                    FROM Visitor v
                    LEFT JOIN VisitorOrganizationVisitStatus vovs ON v.VisitorId = vovs.VisitorId
                    WHERE v.Email = %s
                """, (email,))
                visitor = cur.fetchone()
                if visitor:
                    visitor_id = visitor[0]
                else:
                    return jsonify({'success': False, 'message': 'Visitor not found with the given email.'}), 404
            elif visitor_id:
                # Fetch the visitor details by ID
                cur.execute("""
                    SELECT v.VisitorId, v.FirstName, v.LastName, v.Email, v.Phone,
                           vovs.VisitorFromOrganization, vovs.VisitorFromLocation
                    FROM Visitor v
                    LEFT JOIN VisitorOrganizationVisitStatus vovs ON v.VisitorId = vovs.VisitorId
                    WHERE v.VisitorId = %s
                """, (visitor_id,))
                visitor = cur.fetchone()

            if not visitor:
                return jsonify({'success': False, 'message': 'Visitor not found.'}), 404

            if request.method == 'POST':
                # Extract form data
                data = {
                    'first_name': request.form.get('first_name'),
                    'last_name': request.form.get('last_name'),
                    'email': request.form.get('email'),
                    'phone': request.form.get('phone'),
                    'visitor_organization': request.form.get('visitor_organization'),
                    'visitor_location': request.form.get('visitor_location')
                }

                # Begin transaction
                cur.execute("BEGIN")
                
                try:
                    # Fetch current visitor details to track changes
                    cur.execute("""
                        SELECT FirstName, LastName, Email, Phone 
                        FROM Visitor 
                        WHERE VisitorId = %s
                    """, (visitor_id,))
                    current_visitor_details = cur.fetchone()

                    # Prepare update reason based on changes
                    update_reasons = []
                    if current_visitor_details[0] != data['first_name']:
                        update_reasons.append(f"First Name changed from {current_visitor_details[0]} to {data['first_name']}")
                    if current_visitor_details[1] != data['last_name']:
                        update_reasons.append(f"Last Name changed from {current_visitor_details[1]} to {data['last_name']}")
                    if current_visitor_details[2] != data['email']:
                        update_reasons.append(f"Email changed from {current_visitor_details[2]} to {data['email']}")
                    if current_visitor_details[3] != data['phone']:
                        update_reasons.append(f"Phone changed from {current_visitor_details[3]} to {data['phone']}")

                    # Update basic visitor information
                    cur.execute("""
                        UPDATE Visitor
                        SET FirstName = %s, LastName = %s, Email = %s, Phone = %s
                        WHERE VisitorId = %s
                    """, (
                        data['first_name'], data['last_name'], data['email'], data['phone'],
                        visitor_id
                    ))

                    # Update VisitorOrganizationVisitStatus
                    cur.execute("""
                        UPDATE VisitorOrganizationVisitStatus
                        SET VisitorFromOrganization = %s, VisitorFromLocation = %s
                        WHERE VisitorId = %s
                    """, (
                        data['visitor_organization'], data['visitor_location'], 
                        visitor_id
                    ))

                    # Insert into VisitorUpdateHistory
                    if update_reasons:
                        cur.execute("""
                            INSERT INTO VisitorUpdateHistory 
                            (visitorsid, updatedby, update_reason) 
                            VALUES (%s, %s, %s)
                        """, (
                            visitor_id, 
                            user_id, 
                            '; '.join(update_reasons)
                        ))

                    # Commit transaction
                    cur.execute("COMMIT")
                    return jsonify({'success': True, 'message': 'Visitor updated successfully!'}), 200

                except Exception as e:
                    cur.execute("ROLLBACK")
                    logging.error(f'Error in transaction while editing visitor: {e}')
                    return jsonify({'success': False, 'message': str(e)}), 500

    except Exception as e:
        logging.error(f'Error editing visitor (VisitorId={visitor_id}): {e}')
        return jsonify({'success': False, 'message': 'An error occurred while editing the visitor. Please try again.'}), 500
    finally:
        if conn:
            conn.close()

    # For GET requests, render the template with visitor data
    return render_template('edit_visitor.html', 
                         visitor=visitor,
                         user_id=user_id,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

@app.route('/upload_visitor_photo', methods=['POST'])
def upload_visitor_photo():
    # Check if a photo was uploaded
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No photo uploaded.'}), 400
    
    photo = request.files['photo']

    # Check if the photo has a filename
    if photo.filename == '':
        return jsonify({'success': False, 'error': 'No selected photo.'}), 400

    appointment_id = request.form.get('appointment_id')
    if not appointment_id:
        return jsonify({'success': False, 'error': 'Appointment ID is required'}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error. Please try again later.'}), 500
    
    try:
        with conn.cursor() as cur:
            # First verify if the appointment exists
            cur.execute("""
                SELECT AppointmentId 
                FROM VisitorAppointment 
                WHERE AppointmentId = %s
            """, (appointment_id,))
            
            if not cur.fetchone():
                return jsonify({'success': False, 'error': 'Invalid Appointment ID'}), 404

            # Fetch existing photo filename for the specific appointment
            cur.execute("""
                SELECT InTimePhoto 
                FROM VisitorVisitStatus 
                WHERE AppointmentId = %s
            """, (appointment_id,))
            existing_photo = cur.fetchone()
            existing_photo_filename = existing_photo[0] if existing_photo else None

            # Delete existing photo from the filesystem if it exists
            if existing_photo_filename:
                existing_photo_path = os.path.join('static/visitor_photos', existing_photo_filename)
                if os.path.exists(existing_photo_path):
                    os.remove(existing_photo_path)

            # Generate a new filename for the uploaded photo
            filename, file_extension = os.path.splitext(secure_filename(photo.filename))
            photo_filename = f"{uuid.uuid4().hex}_{filename}{file_extension}"
            photo_path = os.path.join('static/visitor_photos', photo_filename)
            photo.save(photo_path)

            # Update the database with the new photo filename for the specific appointment
            cur.execute("""
                UPDATE VisitorVisitStatus 
                SET InTimePhoto = %s 
                WHERE AppointmentId = %s
            """, (photo_filename, appointment_id))

            # Add to update history
            cur.execute("""
                INSERT INTO VisitorUpdateHistory (
                    visitorsid,
                    updatedby,
                    update_reason,
                    AppointmentId
                )
                SELECT 
                    VisitorId,
                    (SELECT CreatedBy FROM VisitorAppointment WHERE AppointmentId = %s),
                    'Photo Update',
                    AppointmentId
                FROM VisitorVisitStatus
                WHERE AppointmentId = %s
            """, (appointment_id, appointment_id))

            conn.commit()

        return jsonify({'success': True, 'message': 'Photo uploaded successfully!'})

    except Exception as e:
        logging.error(f'Error uploading photo: {e}')
        return jsonify({'success': False, 'error': 'An error occurred while uploading the photo. Please try again.'}), 500

    finally:
        if conn:
            conn.close()

@app.route('/upload_out_time_photo', methods=['POST'])
def upload_out_time_photo():
    if 'photo' not in request.files:
        return jsonify({'success': False, 'error': 'No photo uploaded.'}), 400
    
    photo = request.files['photo']
    
    if photo.filename == '':
        return jsonify({'success': False, 'error': 'No selected photo.'}), 400
    
    visitor_id = request.form.get('visitor_id')
    conn = get_db_connection()
    
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error. Please try again later.'}), 500
    
    try:
        with conn.cursor() as cur:
            # Fetch existing out time photo filename from VisitorVisitStatus
            if visitor_id:
                cur.execute("""
                    SELECT OutTimePhoto 
                    FROM VisitorVisitStatus 
                    WHERE VisitorId = %s 
                    ORDER BY CreatedAt DESC 
                    LIMIT 1
                """, (visitor_id,))
                existing_photo = cur.fetchone()
                existing_photo_filename = existing_photo[0] if existing_photo else None
                
                # Delete existing photo from the filesystem if it exists
                if existing_photo_filename:
                    existing_photo_path = os.path.join('static/out_time_photos', existing_photo_filename)
                    if os.path.exists(existing_photo_path):
                        os.remove(existing_photo_path)
                
                # Generate a new filename for the uploaded photo
                filename, file_extension = os.path.splitext(secure_filename(photo.filename))
                photo_filename = f"{uuid.uuid4().hex}_{filename}{file_extension}"
                photo_path = os.path.join('static/out_time_photos', photo_filename)
                photo.save(photo_path)
                
                # Update the VisitorVisitStatus table with the new photo filename
                cur.execute("""
                    UPDATE VisitorVisitStatus 
                    SET OutTimePhoto = %s 
                    WHERE VisitorId = %s 
                    AND CreatedAt = (
                        SELECT MAX(CreatedAt) 
                        FROM VisitorVisitStatus 
                        WHERE VisitorId = %s
                    )
                """, (photo_filename, visitor_id, visitor_id))
                conn.commit()
        
        return jsonify({'success': True, 'message': 'Out time photo uploaded successfully!'})
    
    except Exception as e:
        logging.error(f'Error uploading out time photo: {e}')
        return jsonify({'success': False, 'error': 'An error occurred while uploading the out time photo. Please try again.'}), 500
    
    finally:
        conn.close()
    
@app.route('/toggle_checkin/<int:visitor_id>', methods=['POST'])
def toggle_checkin(visitor_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Get the current date
            current_date = datetime.now().date()
            
            # Get current status for today's appointment only
            cur.execute("""
                SELECT vvs.VisitStatus, vvs.InTime, vvs.OutTime, vvs.AppointmentId
                FROM VisitorVisitStatus vvs
                JOIN VisitorAppointment va ON vvs.AppointmentId = va.AppointmentId
                WHERE vvs.VisitorId = %s
                AND DATE(va.AppointmentDate) = %s
                ORDER BY vvs.CreatedAt DESC 
                LIMIT 1
            """, (visitor_id, current_date))
            result = cur.fetchone()
            
            if not result:
                return jsonify({'error': 'No valid appointment found for today'}), 404
                
            current_status, in_time, out_time, appointment_id = result
            current_time = datetime.now()
            
            # Only update if the status isn't already 'Inside'
            if current_status != 'Inside' and not in_time:
                cur.execute("""
                    UPDATE VisitorVisitStatus 
                    SET VisitStatus = 'Inside', 
                        InTime = %s 
                    WHERE AppointmentId = %s
                    AND VisitorId = %s
                    RETURNING VisitStatus
                """, (current_time, appointment_id, visitor_id))
                new_status = 'Inside'
            else:
                return jsonify({'error': 'Visitor is already checked in'}), 400
            
            conn.commit()
            return jsonify({
                'success': True, 
                'new_status': new_status,
                'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
    except Exception as e:
        logging.error(f'Error updating check-in for Visitor {visitor_id}: {e}')
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/toggle_checkout/<int:visitor_id>', methods=['POST'])
def toggle_checkout(visitor_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error.'}), 500
    
    try:
        with conn.cursor() as cur:
            # Check if the visitor's status allows for checkout
            cur.execute("""
                SELECT VisitStatus 
                FROM VisitorVisitStatus 
                WHERE VisitorId = %s 
                ORDER BY CreatedAt DESC 
                LIMIT 1
            """, (visitor_id,))
            result = cur.fetchone()
            if not result:
                return jsonify({'success': False, 'error': 'Visitor not found.'}), 404
            
            current_status = result[0]
            logging.info(f'Current status for VisitorId={visitor_id}: {current_status}')
            
            if current_status in ['No Visit', 'Is Gone']:
                return jsonify({'success': False, 'error': 'Cannot check out a visitor with No Visit or who has already checked out.'}), 400
            
            if current_status != 'Inside':
                return jsonify({'success': False, 'error': 'Visitor must be checked in before checking out.'}), 400
            
            check_out_time = datetime.now()
            logging.info(f'Checking out VisitorId={visitor_id} at {check_out_time}')
            
            # Update status to 'Is Gone' in VisitorVisitStatus
            cur.execute("""
                UPDATE VisitorVisitStatus 
                SET OutTime = %s, VisitStatus = 'Is Gone'
                WHERE VisitorId = %s 
                AND CreatedAt = (
                    SELECT MAX(CreatedAt) 
                    FROM VisitorVisitStatus 
                    WHERE VisitorId = %s
                )
            """, (check_out_time, visitor_id, visitor_id))
            
            conn.commit()
            logging.info(f'Successfully checked out VisitorId={visitor_id}')
            return jsonify({'success': True, 'message': 'Visitor checked out successfully!'})
    
    except Exception as e:
        logging.error(f'Error toggling check-out status for VisitorId={visitor_id}: {e}')
        return jsonify({'success': False, 'error': 'An error occurred while updating the check-out status.'}), 500
    
    finally:
        conn.close()


@app.route('/search_visitor')
def search_visitor():
    try:
        email = request.args.get('email')
        appointment_id = request.args.get('appointment_id')
        logging.info(f"Searching for visitor with email: {email} or appointment ID: {appointment_id}")
        
        if not email and not appointment_id:
            logging.warning("No email or appointment ID provided in search request")
            return jsonify({'error': 'Email or appointment ID is required'}), 400
            
        conn = get_db_connection()
        if conn is None:
            logging.error("Failed to establish database connection")
            return jsonify({'error': 'Database connection error'}), 500

        with conn.cursor() as cur:
            # Build the WHERE clause based on search parameters
            where_clause = ""
            params = []
            
            if email and appointment_id:
                where_clause = "WHERE (v.Email ILIKE %s OR va.AppointmentId = %s)"
                params = [f'%{email}%', appointment_id]
            elif email:
                where_clause = "WHERE v.Email ILIKE %s"
                params = [f'%{email}%']
            else:
                where_clause = "WHERE va.AppointmentId = %s"
                params = [appointment_id]

            search_query = f"""
            SELECT 
                v.VisitorId,
                v.FirstName,
                v.LastName,
                v.Email,
                v.Phone,
                v.HostName,
                vvs.VisitDate,
                vvs.VisitPurpose,
                vvs.VisitStatus,
                vvs.InTimePhoto,
                vvs.OutTimePhoto,
                vvs.InTime,
                vvs.OutTime,
                vvs.CreatedAt as visit_created_at,
                vovs.VisitorFromOrganization,
                vovs.VisitorFromLocation,
                vovs.VisitInOrganization,
                vovs.VisitInLocation,
                COALESCE(vzs.zone_status, 'green zone') as zone_status,
                va.AppointmentId,
                va.AppointmentDate,
                va.AppointmentLocation
            FROM Visitor v
            LEFT JOIN VisitorAppointment va ON v.VisitorId = va.VisitorId
            LEFT JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
            LEFT JOIN VisitorOrganizationVisitStatus vovs ON va.AppointmentId = vovs.AppointmentId
            LEFT JOIN Visitor_Zone_Status vzs ON va.AppointmentId = vzs.AppointmentId
            {where_clause}
            ORDER BY va.AppointmentDate DESC, va.CreatedAt DESC
            """
            
            logging.info("Executing main search query")
            cur.execute(search_query, params)
            visitors = cur.fetchall()
            
            if not visitors:
                logging.info(f"No visitors found for search parameters")
                return jsonify({'message': 'No visitors found'}), 404
                
            visitor_list = [{
                'VisitorId': visitor[0],
                'FirstName': visitor[1],
                'LastName': visitor[2],
                'Email': visitor[3],
                'Phone': visitor[4],
                'HostName': visitor[5],
                'VisitDate': visitor[6].strftime('%Y-%m-%d') if visitor[6] else None,
                'VisitPurpose': visitor[7],
                'VisitorStatus': visitor[8],
                'VisitorPhoto': visitor[9],
                'OutTimePhoto': visitor[10],
                'CheckInTime': visitor[11].strftime('%Y-%m-%d %H:%M:%S') if visitor[11] else None,
                'CheckOutTime': visitor[12].strftime('%Y-%m-%d %H:%M:%S') if visitor[12] else None,
                'CreatedAt': visitor[13].strftime('%Y-%m-%d %H:%M:%S') if visitor[13] else None,
                'VisitorOrganization': visitor[14],
                'VisitorLocation': visitor[15],
                'OrganizationName': visitor[16],
                'OrganizationLocation': visitor[17],
                'ZoneStatus': visitor[18],
                'AppointmentId': visitor[19],
                'AppointmentDate': visitor[20].strftime('%Y-%m-%d') if visitor[20] else None,
                'AppointmentLocation': visitor[21]
            } for visitor in visitors]
            
            logging.info(f"Successfully found {len(visitor_list)} visitors")
            return jsonify({'visitors': visitor_list}), 200
            
    except Exception as e:
        logging.error(f"Error searching for visitor: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()
class VisitorSettingsForm(FlaskForm):
    allow_checkout_without_photo = BooleanField('Allow Checkout Without Photo')
    submit = SubmitField('Save Settings')
def get_visitor_settings():
    # Replace this with actual logic to retrieve settings.
    # For example, from a database or configuration file.
    return {
        'allow_checkout_without_photo': False  # Default value
    }

def save_visitor_settings(settings):
    # Replace this with actual logic to save settings.
    print("Settings saved:", settings)

    
     
@app.route('/combined_register_visitor', methods=['GET', 'POST'])
def combined_register_visitor():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Fetch user information including permissions
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    # Get employee company
    conn = get_db_connection()
    employee_company = None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Company FROM Employee 
                WHERE Employee_Id = %s
            """, (user_id,))
            result = cur.fetchone()
            if result:
                employee_company = result[0]
    except Exception as e:
        logging.error(f'Error fetching employee company: {e}')
        flash('Error fetching employee company', 'danger')
    finally:
        if conn:
            conn.close()

    if not employee_company:
        flash('Employee company not found.', 'danger')
        return redirect(url_for('dashboard'))

    today = date.today()

    if request.method == 'POST':
        # Handle photo upload and check-in/out updates
        if 'visitor_photo' in request.files or 'out_time_photo' in request.files or 'check_in_time' in request.form or 'check_out_time' in request.form:
            appointment_id = request.form.get('appointment_id')
            if not appointment_id:
                return jsonify({'success': False, 'error': 'Appointment ID is required'}), 400

            conn = get_db_connection()
            try:
                with conn.cursor() as cur:
                    # First verify if the appointment exists
                    cur.execute("""
                        SELECT AppointmentId 
                        FROM VisitorAppointment 
                        WHERE AppointmentId = %s
                    """, (appointment_id,))
                    
                    if not cur.fetchone():
                        return jsonify({'success': False, 'error': 'Invalid Appointment ID'}), 404

                    update_fields = []
                    update_values = []

                    # Handle visitor photo upload
                    if 'visitor_photo' in request.files:
                        photo = request.files['visitor_photo']
                        if photo.filename != '':
                            filename, file_extension = os.path.splitext(secure_filename(photo.filename))
                            photo_filename = f"{uuid.uuid4().hex}_{filename}{file_extension}"
                            photo_path = os.path.join('static/visitor_photos', photo_filename)
                            photo.save(photo_path)
                            update_fields.append("InTimePhoto = %s")
                            update_values.append(photo_filename)

                    # Handle out time photo upload
                    if 'out_time_photo' in request.files:
                        photo = request.files['out_time_photo']
                        if photo.filename != '':
                            filename, file_extension = os.path.splitext(secure_filename(photo.filename))
                            photo_filename = f"{uuid.uuid4().hex}_{filename}{file_extension}"
                            photo_path = os.path.join('static/visitor_photos', photo_filename)
                            photo.save(photo_path)
                            update_fields.append("OutTimePhoto = %s")
                            update_values.append(photo_filename)

                    # Handle check-in time
                    check_in_time = request.form.get('check_in_time')
                    if check_in_time:
                        update_fields.append("InTime = %s")
                        update_fields.append("VisitStatus = 'Checked In'")
                        update_values.append(check_in_time)

                    # Handle check-out time
                    check_out_time = request.form.get('check_out_time')
                    if check_out_time:
                        update_fields.append("OutTime = %s")
                        update_fields.append("VisitStatus = 'Completed'")
                        update_values.append(check_out_time)

                    if update_fields:
                        # Construct and execute the update query
                        query = f"""
                            UPDATE VisitorVisitStatus 
                            SET {", ".join(update_fields)}
                            WHERE AppointmentId = %s
                        """
                        update_values.append(appointment_id)
                        cur.execute(query, tuple(update_values))

                    conn.commit()
                    return jsonify({'success': True, 'message': 'Updated successfully'})

            except Exception as e:
                logging.error(f'Error updating visitor status: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500
            finally:
                if conn:
                    conn.close()

        # Original visitor registration code
        data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'visit_date': request.form.get('visit_date'),
            'visit_purpose': request.form.get('visit_purpose'),
            'visit_area': request.form.get('visit_area'),
            'host_name': request.form.get('host_name'),
            'visitor_organization': request.form.get('visitor_organization'),
            'visitor_location': request.form.get('visitor_location'),
            'organization_name': employee_company,
            'organization_location': request.form.get('organization_location')
        }

        required_fields = ['first_name', 'last_name', 'email', 'phone', 'visit_date']
        for field in required_fields:
            if not data[field]:
                return jsonify({'success': False, 'error': f'{field.replace("_", " ").title()} is required.'}), 400

        zone_status = 'pending' if data['visit_area'] else 'green zone'
        created_at = datetime.now()

        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection error.'}), 500

        try:
            with conn.cursor() as cur:
                try:
                    visit_date = datetime.strptime(data['visit_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'error': 'Invalid date format, should be YYYY-MM-DD.'}), 400

                new_status = 'Pending' if visit_date >= today else 'No Visit'

                # Check for existing visitor
                cur.execute("""
                    SELECT v.VisitorId, v.FirstName, v.LastName 
                    FROM Visitor v
                    WHERE v.Email = %s OR v.Phone = %s
                """, (data['email'], data['phone']))
                existing_visitor = cur.fetchone()

                if existing_visitor:
                    visitor_id = existing_visitor[0]
                else:
                    # Create new visitor
                    cur.execute("""
                        INSERT INTO Visitor (
                            FirstName, LastName, Email, Phone, 
                            HostName, CreatedBy, CreatedAt, VisitDate
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING VisitorId
                    """, (
                        data['first_name'], data['last_name'], data['email'], 
                        data['phone'], data['host_name'], user_id, created_at, visit_date
                    ))
                    visitor_id = cur.fetchone()[0]

                # Create new appointment
                cur.execute("""
                    INSERT INTO VisitorAppointment (
                        VisitorId, AppointmentDate, AppointmentLocation,
                        CreatedAt, CreatedBy
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING AppointmentId
                """, (
                    visitor_id, visit_date, data['organization_location'],
                    created_at, user_id
                ))
                appointment_id = cur.fetchone()[0]

                # Create new visit status
                cur.execute("""
                    INSERT INTO VisitorVisitStatus (
                        VisitorId, VisitStatus, VisitPurpose, 
                        CreatedBy, CreatedAt, VisitDate,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, new_status, data['visit_purpose'],
                    user_id, created_at, visit_date, appointment_id
                ))

                # Create new organization status
                cur.execute("""
                    INSERT INTO VisitorOrganizationVisitStatus (
                        VisitorId, VisitorFromOrganization, VisitorFromLocation,
                        VisitInOrganization, VisitInLocation, CreatedBy, CreatedAt,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, data['visitor_organization'], data['visitor_location'],
                    data['organization_name'], data['organization_location'], user_id, created_at,
                    appointment_id
                ))

                # Create new zone status
                cur.execute("""
                    INSERT INTO Visitor_Zone_Status (
                        zone_visitor_id, zone_requester_user_id, 
                        zone_visit_area, zone_visit_purpose, 
                        zone_status, zone_request_time,
                        AppointmentId
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    visitor_id, user_id, data['visit_area'],
                    data['visit_purpose'], zone_status, created_at,
                    appointment_id
                ))

                conn.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Visitor appointment registered successfully!', 
                    'visitor_id': visitor_id,
                    'appointment_id': appointment_id
                })

        except Exception as e:
            logging.error(f'Error registering visitor: {e}')
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if conn:
                conn.close()

    # Fetch visitor list
    visitor_list = []
    try:
        conn = get_db_connection()
        if conn is None:
            flash('Database connection error. Please try again later.', 'danger')
            return redirect(url_for('dashboard'))

        with conn.cursor() as cur:
            # Update visit status for past pending visits
            cur.execute("""
                UPDATE VisitorVisitStatus
                SET VisitStatus = 'No Visit'
                WHERE VisitDate < CURRENT_DATE 
                AND VisitStatus = 'Pending'
            """)
            conn.commit()

            base_query = """
            SELECT 
                v.VisitorId,
                v.FirstName,
                v.LastName,
                v.Email,
                v.Phone,
                v.HostName,
                vvs.VisitDate,
                vvs.VisitPurpose,
                vvs.VisitStatus,
                vvs.InTimePhoto,
                vvs.OutTimePhoto,
                vvs.InTime,
                vvs.OutTime,
                vvs.CreatedAt as visit_created_at,
                vovs.VisitorFromOrganization,
                vovs.VisitorFromLocation,
                vovs.VisitInOrganization,
                vovs.VisitInLocation,
                COALESCE(vzs.zone_status, 'green zone') as zone_status,
                va.AppointmentId,
                va.AppointmentDate,
                va.AppointmentLocation,
                vh.updateid as last_update_id,
                vh.update_reason as last_update_reason
            FROM VisitorAppointment va
            INNER JOIN Visitor v ON va.VisitorId = v.VisitorId
            INNER JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
            INNER JOIN VisitorOrganizationVisitStatus vovs ON va.AppointmentId = vovs.AppointmentId
            LEFT JOIN Visitor_Zone_Status vzs ON va.AppointmentId = vzs.AppointmentId
            LEFT JOIN VisitorUpdateHistory vh ON va.AppointmentId = vh.AppointmentId
            ORDER BY va.AppointmentDate DESC, va.CreatedAt DESC
            """
            
            cur.execute(base_query, [employee_company])
            visitors = cur.fetchall()

            if visitors:
                visitor_list = [{
                    'VisitorId': visitor[0],
                    'FirstName': visitor[1],
                    'LastName': visitor[2],
                    'Email': visitor[3],
                    'Phone': visitor[4],
                    'HostName': visitor[5],
                    'VisitDate': visitor[6],
                          'VisitPurpose': visitor[7],
                    'VisitorStatus': visitor[8],
                    'VisitorPhoto': visitor[9],
                    'OutTimePhoto': visitor[10],
                    'CheckInTime': visitor[11],
                    'CheckOutTime': visitor[12],
                    'CreatedAt': visitor[13],
                    'VisitorOrganization': visitor[14],
                    'VisitorLocation': visitor[15],
                    'OrganizationName': visitor[16],
                    'OrganizationLocation': visitor[17],
                    'ZoneStatus': visitor[18],
                    'AppointmentId': visitor[19],
                    'AppointmentDate': visitor[20],
                    'AppointmentLocation': visitor[21],
                    'LastUpdateId': visitor[22],
                    'LastUpdateReason': visitor[23]
                } for visitor in visitors]
            else:
                logging.info('No visitors found in the database.')
    except Exception as query_error:
            logging.error(f'Error executing visitor query: {query_error}')
            flash(f'Error retrieving visitors: {query_error}', 'danger')         

    except Exception as e:
        logging.error(f'Error fetching visitors: {e}')
        flash('An error occurred while fetching visitors. Please try again.', 'danger')
    finally:
        if conn:
            conn.close()

    return render_template('combined_register_visitor.html', 
                         visitors=visitor_list,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access,
                         employee_company=employee_company)

@app.route('/get_dashboard_data', methods=['GET'])
def get_dashboard_data():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'User is not logged in.'}), 401

    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection error.'}), 500

        with conn.cursor() as cur:
            # Query to get visitor status counts
            cur.execute("""
                SELECT vvs.VisitStatus, COUNT(*)
                FROM VisitorVisitStatus vvs
                WHERE vvs.VisitStatus IN ('Pending', 'Inside', 'Is Gone', 'No Visit')
                GROUP BY vvs.VisitStatus
            """)
            visitor_status_counts = {status: count for status, count in cur.fetchall()}

            # Enhanced query to fetch ALL zone statuses dynamically
            cur.execute("""
                WITH VisitorZoneStatus AS (
                    SELECT 
                        COALESCE(
                            NULLIF(TRIM(LOWER(vzs.zone_status)), ''), 
                            'Unspecified Zone'
                        ) as zone_status
                    FROM VisitorAppointment va
                    LEFT JOIN Visitor_Zone_Status vzs ON va.AppointmentId = vzs.AppointmentId
                    JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
                    WHERE vvs.VisitStatus IN ('Pending', 'Inside', 'Is Gone', 'No Visit')
                )
                SELECT 
                    zone_status, 
                    COUNT(*) as zone_count
                FROM VisitorZoneStatus
                GROUP BY zone_status
                ORDER BY zone_count DESC
            """)
            zone_status_data = cur.fetchall()

            # Convert zone status data to dictionary
            zone_status_counts = dict(zone_status_data)

            # Ensure all statuses exist in the result
            visitor_status_counts = {
                'Pending': visitor_status_counts.get('Pending', 0),
                'Inside': visitor_status_counts.get('Inside', 0),
                'Is Gone': visitor_status_counts.get('Is Gone', 0),
                'No Visit': visitor_status_counts.get('No Visit', 0)
            }

            return jsonify({
                'success': True,
                'visitor_status_counts': [
                    visitor_status_counts['Pending'],
                    visitor_status_counts['Inside'],
                    visitor_status_counts['Is Gone'],
                    visitor_status_counts['No Visit']
                ],
                'zone_status_counts': list(zone_status_counts.values()),
                'zone_status_labels': list(zone_status_counts.keys())
            })

    except Exception as e:
        logging.error(f"Error fetching dashboard data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            conn.close()

@app.route('/visitor_settings', methods=['GET', 'POST'])
def visitor_settings():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    form = VisitorSettingsForm()
    settings = get_visitor_settings()

    if form.validate_on_submit():
        allow_checkout_without_photo = form.allow_checkout_without_photo.data
        settings['allow_checkout_without_photo'] = allow_checkout_without_photo
        save_visitor_settings(settings)  # Save to the database
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('visitor_settings'))

    # Populate the form with the current settings
    form.allow_checkout_without_photo.data = settings['allow_checkout_without_photo']
    
    return render_template('visitor_settings.html', 
                         form=form,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

@app.route('/zone-requests', methods=['GET', 'POST'])
def zone_requests_page():
    user_id = session.get('user_id')

    # Check if the user is logged in
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Fetch user information including all necessary settings
            cur.execute("""
                SELECT UserId, ShowForgetPassword, CanViewEmployees, 
                       CanRegisterEmployee, CanRegisterVisitor, 
                       CanRegisterCombined, CanViewVisitors, CanViewUsers,
                       CanAccessZoneRequests, CanAccessVisitorSettings,
                       CanAddCompany, CanAddDepartment, CanAddDesignation,
                       CanAddRole, CanAddZone, CanAddZoneArea, CanQuickRegister,
                       CanAccessRoleAccess
                FROM Users 
                WHERE UserId = %s
            """, (user_id,))
            user = cur.fetchone()

            if user:
                user_id = user[0]
                show_forget_password = user[1]
                can_view_employees = user[2]
                can_register_employee = user[3]
                can_register_visitor = user[4]
                can_register_combined = user[5]
                can_view_visitors = user[6]
                can_view_users = user[7]
                can_access_zone_requests = user[8]
                can_access_visitor_settings = user[9]
                can_add_company = user[10]
                can_add_department = user[11]
                can_add_designation = user[12]
                can_add_role = user[13]
                can_add_zone = user[14]
                can_add_zone_area = user[15]
                can_quick_register = user[16]
                can_access_role_access = user[17]
            else:
                flash('User not found.', 'danger')
                return redirect(url_for('login'))

            # Fetch profile photo
            cur.execute("SELECT Photo FROM Employee WHERE Employee_Id = %s", (user_id,))
            photo_result = cur.fetchone()
            photo_filename = photo_result[0] if photo_result else None

    except Exception as e:
        logging.error(f'Error fetching user data: {e}')
        flash('An error occurred while fetching your data. Please try again.', 'danger')
        return redirect(url_for('dashboard'))
    finally:
        if conn:
            conn.close()

    # Fetch zone requests
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error. Please try again later.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        with conn.cursor() as cur:
            # Handling POST request for approving/rejecting zone requests
            if request.method == 'POST':
                try:
                    data = request.get_json()
                    if not data:
                        return jsonify({'success': False, 'error': 'No JSON data received'}), 400

                    action = data.get('action')
                    zone_id = data.get('zone_id')
                    approver_user_id = user_id
                    zone_action_time = datetime.now()

                    if not all([zone_id, action]):
                        missing = []
                        if not zone_id: missing.append('zone_id')
                        if not action: missing.append('action')
                        return jsonify({
                            'success': False, 
                            'error': f'Missing required fields: {", ".join(missing)}'
                        }), 400

                    # Map actions to zone statuses
                    new_status = ''
                    if action == 'approve':
                        new_status = 'Approved'
                    elif action == 'reject':
                        new_status = 'Rejected'
                    else:
                        return jsonify({'success': False, 'error': 'Invalid action'}), 400

                    # First check if the status is still 'pending'
                    cur.execute("""
                        SELECT zone_status, zone_visit_area
                        FROM visitor_zone_status 
                        WHERE zone_id = %s
                    """, (zone_id,))
                    
                    result = cur.fetchone()
                    if not result:
                        return jsonify({'success': False, 'error': 'Zone request not found'}), 404
                    
                    if result[0] != 'pending':
                        return jsonify({'success': False, 'error': 'This request has already been processed'}), 400

                    # Automatically approve Green Zone requests
                    if result[1].lower().strip() == 'green zone':
                        new_status = 'Approved'
                        action = 'approve'

                    # Update the status 
                    cur.execute("""
                        UPDATE visitor_zone_status 
                        SET zone_status = %s, 
                            zone_approver_user_id = %s, 
                            zone_action_time = %s
                        WHERE zone_id = %s
                    """, (new_status, approver_user_id, zone_action_time, zone_id))
                    
                    conn.commit()
                    return jsonify({'success': True, 'action': action})

                except Exception as e:
                    conn.rollback()
                    logging.error(f'Error processing zone request: {str(e)}')
                    return jsonify({'success': False, 'error': str(e)}), 500

            # Fetch zone request list - Modified to limit to 1 result
            cur.execute("""
                SELECT 
                    vz.zone_id, 
                    vz.zone_visitor_id, 
                    vz.zone_visit_purpose, 
                    vz.zone_visit_area,
                    vz.zone_requester_user_id, 
                    vz.zone_request_time, 
                    vz.zone_status,
                    cz.ZoneName AS company_zone_name,
                    cd.CompanyName
                FROM visitor_zone_status vz
                LEFT JOIN CompanyZones cz ON 
                    CASE 
                        WHEN vz.company_zone_id ~ '^[0-9]+$' 
                        THEN vz.company_zone_id::integer = cz.CompanyZoneID 
                        ELSE LOWER(TRIM(vz.company_zone_id)) = LOWER(TRIM(cz.ZoneName))
                    END
                LEFT JOIN CompanyZoneAreas cza ON LOWER(TRIM(vz.zone_visit_area)) = LOWER(TRIM(cza.VisitAreaName))
                LEFT JOIN CompanyDetails cd ON cza.CompanyID = cd.CompanyID
                ORDER BY 
                    CASE WHEN vz.zone_status = 'pending' THEN 0 ELSE 1 END,
                    vz.zone_request_time DESC
                LIMIT 1
            """)
            zone_requests = cur.fetchall()

        formatted_requests = []
        for req in zone_requests:
            formatted_requests.append({
                'zone_id': req[0],
                'visitor_name': f'Visitor {req[1]}',
                'zone_visit_purpose': req[2],
                'zone_visit_area': req[3],
                'requester_name': req[4],
                'zone_request_time': req[5].strftime('%Y-%m-%d %H:%M:%S') if req[5] else '',
                'zone_status': req[6],
                'company_zone_name': req[7] or 'Not Specified',
                'company_name': req[8] or 'Not Specified',
                'zone_name': req[7] or 'Not Specified'
            })

        return render_template('zone_requests.html', 
                         zone_requests=formatted_requests,
                         user_id=user_id,
                         photo_filename=photo_filename,
                         show_forget_password=show_forget_password,
                         can_view_employees=can_view_employees,
                         can_register_employee=can_register_employee,
                         can_register_visitor=can_register_visitor,
                         can_register_combined=can_register_combined,
                         can_view_visitors=can_view_visitors,
                         can_view_users=can_view_users,
                         can_access_zone_requests=can_access_zone_requests,
                         can_access_visitor_settings=can_access_visitor_settings,
                         can_add_company=can_add_company,
                         can_add_department=can_add_department,
                         can_add_designation=can_add_designation,
                         can_add_role=can_add_role,
                         can_add_zone=can_add_zone,
                         can_add_zone_area=can_add_zone_area,
                         can_quick_register=can_quick_register,
                         can_access_role_access=can_access_role_access)

    except Exception as e:
        logging.error(f'Error fetching zone requests: {str(e)}')
        flash('Error fetching zone requests. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

    finally:
        if conn:
            conn.close()

@app.route('/request-red-zone', methods=['POST'])
def request_red_zone():
    conn = get_db_connection()
    if conn is None:
        return jsonify({'success': False, 'error': 'Database connection error'}), 500

    try:
        zone_visitor_id = request.form.get('zone_visitor_id')
        zone_visit_area = request.form.get('zone_visit_area')
        zone_visit_purpose = request.form.get('zone_visit_purpose')

        zone_requester_user_id = session.get('user_id')
        logging.info(f'Employee ID from session: {zone_requester_user_id}')

        if not zone_visitor_id or not zone_visit_area or not zone_requester_user_id:
            missing_fields = []
            if not zone_visitor_id:
                missing_fields.append('Visitor ID')
            if not zone_visit_area:
                missing_fields.append('Visit Area')
            if not zone_requester_user_id:
                missing_fields.append('Employee ID')

            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            return jsonify({'success': False, 'error': error_message}), 400

        try:
            zone_visitor_id = int(zone_visitor_id)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid visitor ID format'}), 400

        with conn.cursor() as cur:
            cur.execute("SELECT visitorid FROM Visitor WHERE visitorid = %s", (zone_visitor_id,))
            if not cur.fetchone():
                return jsonify({'success': False, 'error': 'Visitor not found'}), 404

            cur.execute("""
                INSERT INTO Visitor_Zone_Status (
                    zone_visitor_id,
                    zone_requester_user_id,
                    zone_visit_area,
                    zone_visit_purpose,
                    zone_status,
                    zone_request_time
                ) VALUES (%s, %s, %s, %s, 'pending', CURRENT_TIMESTAMP)
                RETURNING zone_id
            """, (
                zone_visitor_id,
                zone_requester_user_id,
                zone_visit_area,
                zone_visit_purpose
            ))

            new_zone_id = cur.fetchone()[0]
            conn.commit()

            return jsonify({
                'success': True,
                'message': 'Red Zone request submitted successfully!',
                'zone_id': new_zone_id
            })

    except Exception as e:
        conn.rollback()
        logging.error(f'Error submitting red zone request: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        if conn:
            conn.close()

            
@app.route('/get_visitor_details/<int:visitor_id>', methods=['GET'])
def get_visitor_details(visitor_id):
    if not session.get('user_id'):
        return jsonify({'success': False, 'error': 'User not logged in'}), 401
    
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({'success': False, 'error': 'Database connection error'}), 500
        
        with conn.cursor() as cur:
            # Modified query to ensure we get the most recent check-in time
            cur.execute("""
                WITH LatestAppointment AS (
                    SELECT AppointmentId
                    FROM VisitorAppointment
                    WHERE VisitorId = %s
                    ORDER BY AppointmentDate DESC, CreatedAt DESC
                    LIMIT 1
                )
                SELECT 
                    v.VisitorId,
                    v.FirstName,
                    v.LastName,
                    v.Email,
                    v.Phone,
                    va.AppointmentDate as VisitDate,
                    vvs.VisitPurpose,
                    v.HostName,
                    vvs.VisitStatus,
                    COALESCE(vvs.InTime, CURRENT_TIMESTAMP) as InTime,
                    vvs.OutTime,
                    vvs.InTimePhoto,
                    COALESCE(vzs.zone_status, 'green zone') as zone_status,
                    vzs.zone_visit_area,
                    COALESCE(vovs.VisitInOrganization, 'N/A') as VisitInOrganization,
                    va.AppointmentId,
                    vvs.OutTimePhoto,
                    vzs.company_zone_id as zone_id
                FROM Visitor v
                JOIN VisitorAppointment va ON v.VisitorId = va.VisitorId
                JOIN VisitorVisitStatus vvs ON va.AppointmentId = vvs.AppointmentId
                LEFT JOIN Visitor_Zone_Status vzs ON va.AppointmentId = vzs.AppointmentId
                LEFT JOIN VisitorOrganizationVisitStatus vovs ON va.AppointmentId = vovs.AppointmentId
                WHERE va.AppointmentId = (SELECT AppointmentId FROM LatestAppointment)
            """, (visitor_id,))
            
            visitor = cur.fetchone()
            
            if visitor:
                # Format the response with immediate check-in time
                visitor_data = {
                    'name': f"{visitor[1]} {visitor[2]}",
                    'email': visitor[3],
                    'phone': visitor[4],
                    'visit_date': visitor[5].strftime('%Y-%m-%d') if visitor[5] else None,
                    'visit_purpose': visitor[6],
                    'host_name': visitor[7],
                    'visitor_status': visitor[8],
                    'check_in_time': visitor[9].strftime('%Y-%m-%d %H:%M:%S') if visitor[9] else None,
                    'check_out_time': visitor[10].strftime('%Y-%m-%d %H:%M:%S') if visitor[10] else None,
                    'photo': url_for('static', filename=f'visitor_photos/{visitor[11]}') if visitor[11] else None,
                    'zone_status': visitor[12],
                    'zone_visit_area': visitor[13] if visitor[13] else 'N/A',
                    'visit_in_organization': visitor[14],
                    'appointment_id': visitor[15],
                    'out_time_photo': url_for('static', filename=f'visitor_photos/{visitor[16]}') if visitor[16] else None,
                    'zone_id': visitor[17] or 'N/A'
                }
                
                # Commit any pending changes to ensure we have the latest data
                conn.commit()
                return jsonify({'success': True, 'visitor': visitor_data})
            
            return jsonify({'success': False, 'error': 'Visitor not found'}), 404
        
    except Exception as e:
        logging.error(f'Error fetching visitor details: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
