"""
Admin tools views (system admin and bulk upload utilities).
"""
from .utils import *
from .auth import is_system_admin


@user_passes_test(is_system_admin)
def system_admin_school_list(request):
    schools = School.objects.all().annotate(
        student_count=Count('students')
    )
    return render(request, 'school_app/admin_tools/school_list.html', {'schools': schools})

@user_passes_test(is_system_admin)
def system_admin_school_add(request):
    if request.method == 'POST':
        form = SchoolAdminRegistrationForm(request.POST)
        if form.is_valid():
            form.save(created_by=request.user)
            messages.success(request, "School and admin account created successfully!")
            return redirect('system_admin_school_list')
    else:
        form = SchoolAdminRegistrationForm()
    return render(request, 'school_app/manage/school_add.html', {'form': form})

@user_passes_test(is_system_admin)
def system_admin_student_list(request, school_id=None):
    if school_id:
        students = Student.objects.filter(school_id=school_id)
    else:
        students = Student.objects.all()
    return render(request, 'school_app/students_mgmt/student_list.html', {'students': students})

@user_passes_test(is_system_admin)
def system_admin_marks_list(request, school_id=None):
    if school_id:
        marks = Marks.objects.filter(student__school_id=school_id)
    else:
        marks = Marks.objects.all()
    return render(request, 'school_app/marks/marks_list.html', {'marks': marks})


@login_required
def school_add(request):
    if request.user.is_system_admin:
        return redirect('system_admin_school_add')

    if School.objects.filter(admin=request.user).exists():
        messages.warning(request, "You already have a school registered.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            school = form.save(commit=False)
            school.admin = request.user
            school.save()
            messages.success(request, "School created successfully!")
            return redirect('dashboard')
    else:
        form = SchoolForm()

    return render(request, 'school_app/manage/school_add.html', {'form': form})


@login_required
def upload_student_data(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']

        # File upload validation
        allowed_extensions = ('.xlsx', '.xls')
        if not excel_file.name.lower().endswith(allowed_extensions):
            messages.error(request, 'Only Excel files (.xlsx, .xls) are allowed.')
            return redirect('upload_student_data')
        max_size = 5 * 1024 * 1024  # 5 MB
        if excel_file.size > max_size:
            messages.error(request, 'File size exceeds 5 MB limit.')
            return redirect('upload_student_data')

        try:
            # Load the Excel file into a pandas DataFrame
            df = pd.read_excel(excel_file, engine='openpyxl')

            successfully_created = 0  # Counter for successfully created students
            roll_number_errors = []  # Store errors related to duplicate roll numbers

            for index, row in df.iterrows():
                name = row['name']
                roll_number = row['roll_number']
                class_name = row['class_name']
                #school_name = row['school_name']
                school_name =""
                # Check if roll_number is unique
                if Student.objects.filter(roll_number=roll_number).exists():
                    roll_number_errors.append(f"Roll number {roll_number} already exists. Skipping this student.")
                    continue  # Skip to the next student if roll number is duplicate

                try:
                    # Get the School instance (assuming school_name exists in the DataFrame)
                    #school = School.objects.get(name=school_name)

                    # Create the student object
                    student = Student.objects.create(
                        school_id=request.user.administered_school.id,
                        name=name,
                        roll_number=roll_number,
                        class_name=class_name,
                        password=make_password('1234')
                    )
                    successfully_created += 1
                except Exception as e:
                    messages.error(request, f"Error processing the file: {str(e)}")
                    continue
                #except School.DoesNotExist:
                #     messages.error(request, f"School '{school_name}' not found for student {name}.")
                #     continue  # Skip this student if the school doesn't exist

            # Display success or error messages
            if successfully_created > 0:
                messages.success(request, f"{successfully_created} students uploaded successfully.")
                log_activity(request, 'UPLOAD', f'Student data uploaded: {successfully_created} students created')
            if roll_number_errors:
                for error in roll_number_errors:
                    messages.warning(request, error)

            return redirect('student_list')  # Redirect to the page displaying student list or another view

        except Exception as e:
            messages.error(request, f"Error processing the file: {str(e)}")
            return redirect('upload_student_data')  # Redirect back to the upload form if any error occurs

    else:
        form = ExcelFileUploadForm()

    return render(request, 'school_app/misc/upload_student_data.html', {'form': form})


@login_required
def upload_school_users(request):
    # You can also change this to request.user.is_district_user if you shifted from groups
    if request.user.groups.filter(name='Collector').exists():

        if request.method == 'POST' and request.FILES.get('excel_file'):
            excel_file = request.FILES['excel_file']
            successfully_created = 0  # Counter

            try:
                # Load Excel data
                df = pd.read_excel(excel_file, engine='openpyxl')

                # Optional: check required columns
                required_cols = {'email', 'username', 'password', 'school_name', 'nic_code', 'block_id'}
                if not required_cols.issubset(set(df.columns)):
                    messages.error(request, "Excel must contain columns: email, username, password, school_name, nic_code, block_id")
                    return redirect('upload_school_users')

                for index, row in df.iterrows():
                    email = str(row['email']).strip()
                    username = str(row['username']).strip()
                    password = str(row['password']).strip()
                    school_name = str(row['school_name']).strip()
                    nic_code = str(row['nic_code']).strip() if not pd.isna(row['nic_code']) else ''
                    block_id = row['block_id']

                    # Skip if email or block_id is missing
                    if not email or pd.isna(block_id):
                        messages.warning(request, f"Row {index+2}: Missing email or block_id. Skipped.")
                        continue

                    try:
                        # Get Block from block_id
                        try:
                            block = Block.objects.get(id=block_id)
                        except Block.DoesNotExist:
                            messages.warning(request, f"Row {index+2}: Block with ID {block_id} not found. Skipped.")
                            continue

                        # Get or create user
                        if CustomUser.objects.filter(email=email).exists():
                            user1 = CustomUser.objects.get(email=email)
                        else:
                            user1 = CustomUser.objects.create_user(
                                email=email,
                                username=username,
                                password=password,
                                is_system_admin=False,
                                is_school_user=True,   # mark as school user
                                is_block_user=False,
                                is_district_user=False
                            )

                        # Create or get School
                        school, created = School.objects.get_or_create(
                            admin=user1,
                            defaults={
                                'name': school_name,
                                'created_by': request.user,
                                'block': block,
                                'nic_code': nic_code
                            }
                        )

                        # If school already existed, optionally update fields
                        if not created:
                            school.name = school_name
                            school.block = block
                            school.nic_code = nic_code
                            school.save()

                        successfully_created += 1

                    except IntegrityError as e:
                        messages.error(request, f"Row {index+2}: Error creating user/school for {email}: {e}")
                        continue

                if successfully_created > 0:
                    messages.success(request, f"{successfully_created} school users uploaded/updated successfully.")
                else:
                    messages.warning(request, "No users were created. Please check the Excel file and try again.")

                return redirect('collector_dashboard')

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
                return redirect('upload_school_users')

        else:
            form = ExcelFileUploadForm()

        return render(request, 'school_app/misc/upload_users.html', {'form': form})

    else:
        return HttpResponseForbidden("You are not authorized to access this page.")


#11/01/2025
@login_required
def update_block_name_from_excel(request):
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']

        try:
            # Read the Excel file using pandas
            df = pd.read_excel(excel_file)

            updates = []
            # Iterate over rows in the DataFrame
            for _, row in df.iterrows():
                school_name = row['School Name']
                block_name = row['Block Name']

                try:
                    # Find the school by name
                    school = School.objects.get(name=school_name)
                    school.Block_Name = block_name  # Update Block Name
                    school.save()  # Save the updated School object
                    updates.append(f'Updated {school_name}')
                except School.DoesNotExist:
                    updates.append(f'{school_name} not found')

            return JsonResponse({'updates': updates})

        except Exception as e:
            return JsonResponse({'error': f'Error processing file: {str(e)}'}, status=400)

    return render(request, 'school_app/manage/update_block_name_form.html')


@login_required
def download_sample_student_excel(request):
    """Return a sample Excel file for bulk student upload."""
    import io
    sample_data = {
        'name':        ['Sushil Agrawal',   'Bhaskar Mishra',   'Priya Sharma'],
        'roll_number': ['202510123456',      '202510123457',      '202510123458'],
        'class_name':  ['10',               '10',               '9'],
    }
    df = pd.DataFrame(sample_data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Students')
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sample_student_upload.xlsx"'
    return response


@login_required
def download_sample_school_excel(request):
    """Return a sample Excel file for bulk school user upload."""
    import io
    sample_data = {
        'email':       ['school01@example.com', 'school02@example.com'],
        'username':    ['SCH01_TONK',           'SCH02_TONK'],
        'password':    ['School@123',            'School@456'],
        'school_name': ['GSSS TONK CITY (221942)', 'GPS NEWAI (221943)'],
        'nic_code':    ['221942',                '221943'],
        'block_id':    [1,                       2],
    }
    df = pd.DataFrame(sample_data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Schools')
    buf.seek(0)
    response = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sample_school_upload.xlsx"'
    return response
