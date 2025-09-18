import pandas as pd
import random
from faker import Faker
import string
from datetime import datetime, timedelta
import hashlib
import numpy as np
from tqdm import tqdm

# Set random seed for reproducibility
random.seed(42)
Faker.seed(42)  # Seed Faker to ensure consistent fake data generation

# Initialize Faker instance
fake = Faker()


##### User Data Generation #####
# Hashing function for passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_random_password():
    """Generate a random password with a mix of letters, digits, and special characters."""
    length = random.randint(8, 12)
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
    while True:
        password = ''.join(random.choice(characters) for _ in range(length))
        # Ensure the password contains at least one letter, one digit, and one special character
        if (any(c.isalpha() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?/~`" for c in password)):
            return password


def generate_username(first_name, middle_name, last_name, role):
    """Generate consistent username based on name components and role"""
    # Clean name components
    first = first_name.lower().replace("'", "").replace(" ", "")
    middle = middle_name[0].lower() if middle_name else ''
    last = last_name.lower().replace("'", "").replace(" ", "")
    
    # Role-specific username patterns
    if role == 'teacher':
        # tea_john.smith
        username = f"tea_{first[:4]}.{last[:6]}"
    elif role == 'student':
        # stu_jsmith + last 2 digits of first name length and last name length
        # This creates uniqueness without needing user_id
        unique_suffix = f"{len(first)%10}{len(last)%10}"
        username = f"stu_{first[0]}{last[:7]}{unique_suffix}"
    elif role == 'guardian':
        # gua_j.smith
        username = f"gua_{first[0]}.{last[:8]}"
    elif role == 'school_admin':
        # adm_johns
        username = f"adm_{first[:3]}{last[:4]}"
    elif role == 'district_admin':
        # dis_jsmith
        username = f"dis_{first[0]}{last[:9]}"
    else:
        # Default pattern
        username = f"{first[0]}{middle}{last[:8]}" if middle else f"{first[0]}{last[:10]}"
    
    return username[:20]  # Ensure reasonable length


def generate_users():
    """Generate user data"""
    users = []
    user_id = 1
    
    # Define number of each role
    role_counts = {
        'teacher': 200,
        'student': 3000,
        'guardian': 5000,
        'school_admin': 20,
        'district_admin': 1
    }

    # Ensure usernames and emails are unique
    used_usernames = set()
    used_emails = set()


 # Generate all names first to ensure consistency
    all_names = {}
    for role, count in role_counts.items():
        role_names = []
        for _ in range(count):
            first_name = fake.first_name()
            middle_name = fake.first_name() if random.random() < 0.3 else None
            last_name = fake.last_name()
            role_names.append((first_name, middle_name, last_name))
        all_names[role] = role_names

    role_settings = {
        'teacher': {'active_weight': 0.99, 'login_prob': 0.98},
        'student': {'active_weight': 0.97, 'login_prob': 0.95},
        'guardian': {'active_weight': 0.9, 'login_prob': 0.85},
        'school_admin': {'active_weight': 1.0, 'login_prob': 1.0},
        'district_admin': {'active_weight': 1.0, 'login_prob': 1.0}
    }

    # Generate users for each role
    for role, count in role_counts.items():
        settings = role_settings[role]
        role_names = all_names[role]
        
        for i in range(count):
            first_name, middle_name, last_name = role_names[i]
            
            # Generate username based on future name data
            username = generate_username(first_name, middle_name, last_name, role)
            
            # Ensure uniqueness
            original_username = username
            suffix = 1
            while username in used_usernames:
                username = f"{original_username}{suffix}"
                suffix += 1
            used_usernames.add(username)
            
            # Generate email
            email = f"{username}@{fake.domain_name()}"
            suffix = 1
            while email in used_emails:
                email = f"{username}{suffix}@{fake.domain_name()}"
                suffix += 1
            used_emails.add(email)
            
            # Generate password
            password = generate_random_password()
            hashed_password = hash_password(password)

            users.append({
                "user_id": user_id,
                "username": username,
                "password": hashed_password,
                "plain_password": password,
                "email": email,
                "role": role,
                "is_active": True if random.random() < settings['active_weight'] else False,
                "last_login": fake.date_time_between(start_date='-1y', end_date='now') 
                             if random.random() < settings['login_prob'] else None,
                "created_at": fake.date_time_between(start_date='-3y', end_date='now')
            })
            user_id += 1
            
    return pd.DataFrame(users), all_names


def save_data(df):
    """Save the generated user data to a CSV file"""
    print("Saving user data to CSV...")

    # Save to CSV according to role
    roles = ['teacher', 'student', 'guardian', 'school_admin', 'district_admin']
    for role in roles:
        df[df['role'] == role].to_csv(f"{role}s.csv", index=False)

    # Save full user data to a single CSV for reference (including passwords for debugging)
    df.to_csv("all_users_with_passwords.csv", index=False)

    # Save full user data without passwords for production use
    df.drop(columns=['plain_password']).to_csv("all_users.csv", index=False)


##### Generate Guardian Data #####
def generate_guardians(user_df, all_names):
    """ Generate guardian data linked to students """
    guardian_users = user_df[user_df['role'] == 'guardian']
    guardians = []
    role_names = all_names['guardian']
    
    for i, (_, user_row) in enumerate(guardian_users.iterrows(), 1):
        first_name, middle_name, last_name = role_names[i-1]
        guardians.append({
            "guardian_id": i,
            "user_id": user_row['user_id'],
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "phone_number": f"({random.randint(200, 999)}) {random.randint(200,999)}-{random.randint(1000, 9999)}"
        })
    
    return pd.DataFrame(guardians)


##### Generate Teacher Data #####
def generate_teachers(user_df, all_names, school_ids):
    """Generate teacher data with matching names"""
    teacher_users = user_df[user_df['role'] == 'teacher']
    teachers = []
    role_names = all_names['teacher']

    school_ids_by_type = {
        "elementary": [1,2,3,4],
        "middle": [5,6,7],
        "high": [8,9],
        "special_ed": [10]
    }

    teacher_allocation = {
        "elementary": (school_ids_by_type["elementary"], 88),
        "middle": (school_ids_by_type["middle"], 48),
        "high": (school_ids_by_type["high"], 60),
        "special_ed": (school_ids_by_type["special_ed"], 4)
    }

    school_teacher_slots = []
    for school_type, (school_ids, slots) in teacher_allocation.items():
        count_per_school = slots // len(school_ids)
        for school_id in school_ids:
            school_teacher_slots.extend([school_id] * count_per_school)
    
    random.shuffle(school_teacher_slots)
    
    for i, (_, user_row) in enumerate(teacher_users.iterrows(), 1):
        if i > len(school_teacher_slots):
            break
        school_id = school_teacher_slots[i-1]
        first_name, middle_name, last_name = role_names[i-1]

        phone_number = f"({random.randint(200, 999)}) {random.randint(200,999)}-{random.randint(1000, 9999)}"
        teachers.append({
            "teacher_id": i,
            "user_id": user_row['user_id'],
            "school_id": school_id,
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "employment_type": random.choices(
                ['full-time', 'part-time', 'substitute'],
                weights=[0.7, 0.2, 0.1]
            )[0],
            "salary": round(random.uniform(40000, 80000), 2),
            "join_date": fake.date_between(start_date='-10y', end_date='-1y')
        })
    
    return pd.DataFrame(teachers)


def generate_students(user_df, all_names, df_teachers, num_student=3000):
    """Generate student data with matching names and links to guardians and schools"""
    # Get student users
    student_users = user_df[user_df['role'] == 'student']

    # Create mapping of school_id to teachers at that school grouped by grade levels they teach
    school_teachers = {}
    grade_teacher_map = {}  # {school_id: {grade: [teacher_ids]}}
    
    for _, row in df_teachers.iterrows():
        school_id = row["school_id"]
        if school_id not in school_teachers:
            school_teachers[school_id] = []
            grade_teacher_map[school_id] = {}
        school_teachers[school_id].append(row["teacher_id"])
        
        # Determine which grades this teacher can teach based on school type
        if school_id in [1, 2, 3, 4]:  # Elementary schools
            grades = ["K", "1", "2", "3", "4", "5"]
        elif school_id in [5, 6, 7]:  # Middle schools
            grades = ["6", "7", "8"]
        elif school_id in [8, 9]:  # High schools
            grades = ["9", "10", "11", "12"]
        else:  # Special ed
            grades = ["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
            
        for grade in grades:
            if grade not in grade_teacher_map[school_id]:
                grade_teacher_map[school_id][grade] = []
            grade_teacher_map[school_id][grade].append(row["teacher_id"])

    students = []
    student_id = 1

    student_names = all_names["student"]

    # Create homeroom groups - {school_id: {grade: {homeroom_id: {'teacher_id': X, 'students': []}}}}
    homerooms = {}
    
    for i, (_, user_row) in enumerate(student_users.iterrows()):
        if i >= num_student:
            break

        # Get the pre-generated names
        first_name, middle_name, last_name = student_names[i]

        # Assign school - elementary (1-4), middle (5-7), high (8-9), special (10)
        grade = random.choice(["K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        if grade in ["K", "1", "2", "3", "4", "5"]:
            # Elementary school (IDs 1-4)
            school_id = random.choice([1, 2, 3, 4])
        elif grade in ["6", "7", "8"]:
            # Middle school (IDs 5-7)
            school_id = random.choice([5, 6, 7])
        else:
            # High school (IDs 8-9)
            school_id = random.choice([8, 9])
        # 5% chance of special education
        if random.random() < 0.05:
            school_id = 10  # Special ed school
        
        # Initialize homeroom structure for this school/grade if needed
        if school_id not in homerooms:
            homerooms[school_id] = {}
        if grade not in homerooms[school_id]:
            homerooms[school_id][grade] = {}
        
        # Find or create a homeroom for this student
        homeroom_assigned = False
        homeroom_teacher_id = None
        homeroom_id = None
        
        # Check if there's an existing homeroom with space (max 25 students)
        for h_id, h_data in homerooms[school_id][grade].items():
            if len(h_data['students']) < 25:
                homeroom_teacher_id = h_data['teacher_id']
                homeroom_id = h_id
                h_data['students'].append(student_id)
                homeroom_assigned = True
                break
                
        # If no available homeroom, create a new one
        if not homeroom_assigned:
            # Get available teachers for this grade
            available_teachers = grade_teacher_map.get(school_id, {}).get(grade, [])
            if available_teachers:
                # Try to find a teacher who isn't already a homeroom teacher for this grade
                existing_homeroom_teachers = [h['teacher_id'] for h in homerooms[school_id][grade].values()]
                candidates = [t for t in available_teachers if t not in existing_homeroom_teachers]
                
                if candidates:
                    homeroom_teacher_id = random.choice(candidates)
                else:
                    # If all teachers are already homeroom teachers, just pick one
                    homeroom_teacher_id = random.choice(available_teachers)
                
                homeroom_id = len(homerooms[school_id][grade]) + 1
                homerooms[school_id][grade][homeroom_id] = {
                    'teacher_id': homeroom_teacher_id,
                    'students': [student_id]
                }
            else:
                homeroom_teacher_id = None
                homeroom_id = None

        # Generate date of birth based on grade level
        current_year = datetime.now().year
        if grade == 'K':
            birth_year = current_year - 5
        elif grade in ['1','2','3','4','5']:
            birth_year = current_year - (int(grade) + 5)
        elif grade in ['6','7','8']:
            birth_year = current_year - (int(grade) + 5)
        else:  # High school
            birth_year = current_year - (int(grade) + 4)
        
        # Add some variation (students can be 1 year older or younger)
        birth_year += random.randint(-1, 1)

        # Generate full date of birth
        dob = fake.date_between_dates(
            date_start=datetime(birth_year-1, 1, 1),
            date_end=datetime(birth_year, 12, 31)
        )
                                         
        students.append({
            "student_id": student_id,
            "user_id": user_row['user_id'],
            "school_id": school_id,
            "first_name": first_name,
            "middle_name": middle_name if random.random() < 0.3 else None,
            "last_name": last_name,
            "date_of_birth": dob.strftime('%Y-%m-%d'),
            "grade_level": grade,
            "homeroom_id": homeroom_id,
            "homeroom_teacher_id": homeroom_teacher_id
        })
        student_id += 1
    
    return pd.DataFrame(students), homerooms


##### Generate Guardian and Student Relationships #####
def generate_guardian_student_relationships(df_students, df_guardians, max_guardians_per_student=2):
    """ Generate guardian-student relationships """
    relationships = []

    guardian_ids = df_guardians['guardian_id'].tolist()

    # Track which guardians have been assigned to students
    guardian_assignments = {guardian_id: [] for guardian_id in guardian_ids}

    for student_id in df_students['student_id']:
        # Determing number of guardians for this student (1-2 normally, sometimes more)
        num_guardians = 1
        if random.random() < 0.5:  # 50% chance to have a second guardian
            num_guardians = 2
        elif random.random() < 0.01:  # 1% chance to have 3 guardians (rare case)
            num_guardians = 3
        
        num_guardians = min(num_guardians, max_guardians_per_student)

        # Select guardians that aren't already assigned to this student
        available_guardians = [
            gid for gid in guardian_ids
            if student_id not in guardian_assignments[gid]  
        ]

        # If we don't have enough available guardians, reduce the number
        num_guardians = min(num_guardians, len(available_guardians))

        if num_guardians == 0:
            continue  # No available guardians to assign

        selected_guardians = random.sample(available_guardians, num_guardians)

        # Assign relationship types
        relationship_types = []
        if num_guardians == 1:
            relationship_types.append(random.choice(['mother', 'father', 'grandmother', 'grandfather', 'others']))
        else:
            combo = random.choice([
                [ 'mother', 'father' ],
                [ 'mother', 'grandmother' ],
                [ 'father', 'grandfather' ],
                [ 'father', 'grandmother' ],
                [ 'grandmother', 'grandfather' ]
            ])
            if num_guardians > 2:
                combo.append('others')
            relationship_types = combo
        
        for i, guardian_id in enumerate(selected_guardians):
            relationships.append({
                "guardian_id": guardian_id,
                "student_id": student_id,
                "relationship": relationship_types[i] if i < len(relationship_types) else 'others'
            })
            guardian_assignments[guardian_id].append(student_id)
    return pd.DataFrame(relationships)


##### Generate Admin Data #####
def generate_admins(user_df, all_names, df_schools):
    """ Generate admin data """
    # Get school admin users
    school_admin_users = user_df[user_df['role'] == 'school_admin']

    # Get district admin users
    district_admin_users = user_df[user_df['role'] == 'district_admin']

    admins = []
    admin_id = 1

    # Get school IDs from the schools dataframe
    school_ids = df_schools["school_id"].tolist()

    # Get pre-generated names for school and district admins
    school_admin_names = all_names['school_admin'] 
    district_admin_names = all_names['district_admin']
    
    # Generate district admin
    for i, (_, user_row) in enumerate(district_admin_users.iterrows()):
        if i >= len(district_admin_names):
            break
        # Get the pre-generated names
        first_name, middle_name, last_name = district_admin_names[i]
        phone_number = f"({random.randint(200, 999)}) {random.randint(200,999)}-{random.randint(1000, 9999)}"

        admins.append({
            "administrator_id": admin_id,
            "user_id": user_row['user_id'],
            "school_id": None,  # District admin has no specific school
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "phone_number": phone_number,
            "employment_type": 'full-time',
            "salary": round(random.uniform(100000, 200000), 2),
            "join_date": fake.date_between(start_date='-10y', end_date='-1y'),
            "supervisor_id": None  # District admin has no supervisor
        })
        admin_id += 1

    # Assign two school admins for each school
    school_admin_count = 0
    school_admin_index = 0

    for school_id in school_ids:
        for j in range(2):
            if school_admin_index >= len(school_admin_names):
                print(f"Warning: Not enough school admin names to assign for school {school_id}.")
                break

            # Get the pre-generated names for school admins
            user_row = school_admin_users.iloc[school_admin_index]
            school_admin_index += 1
            
            # Get the pre-generated names
            name_index = school_admin_count % len(school_admin_names)
            first_name, middle_name, last_name = school_admin_names[name_index]
            phone_number = f"({random.randint(200, 999)}) {random.randint(200,999)}-{random.randint(1000, 9999)}"

            admins.append({
                "administrator_id": admin_id,
                "user_id": user_row['user_id'],
                "school_id": school_id,
                "first_name": first_name,
                "middle_name": middle_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "employment_type": "full-time",
                "salary": round(random.uniform(90000, 120000), 2),
                "join_date": fake.date_between(start_date='-10y', end_date='-1y'),
                "supervisor_id": 1
            })
            admin_id += 1
            school_admin_count += 1
    
    return pd.DataFrame(admins)


##### Generate District Data #####
def generate_districts(superintendent_id = 1):
    """ Generate district data with admin links """
    district_data = {
        "district_id": 1,
        "name": f"{fake.city()} Unified School District",
        "superintendent_id": superintendent_id
    }
    
    return pd.DataFrame([district_data])


def generate_schools(num_schools=10, district_id=1, principal_ids=None):
    """ Generate school data linked to districts and admins """
    schools = []
    school_id = 1

    # Elementary Schools (4)
    for i in range(4):
        schools.append({
            "school_id": school_id,
            "district_id": 1,
            "name": f"{fake.last_name()} Elementary School",
            "school_type": "elementary",
            "address": fake.street_address(),
            "city": "San Jose",
            "state": "CA",
            "zip": random.randint(95002, 95196),
            "principal_id": i+1
        })
        school_id += 1
    
    # Middle Sschools (3)
    for i in range(3):
        schools.append({
            "school_id": school_id,
            "district_id": district_id,
            "name": f"{fake.last_name()} Middle School",
            "school_type": "middle",
            "address": fake.street_address(),
            "city": "San Jose",
            "state": "CA",
            "zip": random.randint(95002, 95196),
            "principal_id": i+5
        })
        school_id += 1
    
    # High Schools (2)
    for i in range(2):
        schools.append({
            "school_id": school_id,
            "district_id": 1,
            "name": f"{fake.last_name()} High School",
            "school_type": "high",
            "address": fake.street_address(),
            "city": "San Jose",
            "state": "CA",
            "zip": random.randint(95002, 95196),
            "principal_id": i+8
        })
        school_id += 1
    
    # Special Education Schools (1)
    schools.append({
        "school_id": school_id,
        "district_id": district_id,
        "name": f"{fake.last_name()} Special Education School",
        "school_type": "special_ed",
        "address": fake.street_address(),
        "city": "San Jose",
        "state": "CA",
        "zip": random.randint(95002, 95196),
        "principal_id": 10
    })
    return pd.DataFrame(schools)

def update_schools_with_principals(schools_df, admin_df):
    """Update schools with the correct principal_id from admin_df"""
    for index, row in schools_df.iterrows():
        school_id = row['school_id']
        # Get admins for this school
        school_admins = admin_df[admin_df['school_id'] == school_id]
        
        if not school_admins.empty:
            # Use the first admin as the principal
            principal_id = school_admins.iloc[0]['administrator_id']
            schools_df.at[index, 'principal_id'] = principal_id
        
    return schools_df


def generate_course_schedule():
    return [
        {"start_time": "8:30", "end_time": "9:15"},  
        {"start_time": "9:25", "end_time": "10:10"},  
        {"start_time": "10:20", "end_time": "11:05"},  
        {"start_time": "11:15", "end_time": "12:00"},  
        {"start_time": "13:00", "end_time": "13:50"},  
        {"start_time": "14:00", "end_time": "14:45"}   
    ]


def generate_courses():
    subjects = ["Math", "Science", "English", "History", "Art", "PE", "Music", "Computers"]
    course_catalog = []
    course_id = 1
    for subject in subjects:
        course_catalog.append({
            "course_id": course_id,
            "name": subject,
        })
        course_id += 1
    return pd.DataFrame(course_catalog)


##### Schedule Slots #####
# TIME_SLOTS = [f"Slot_{i+1}" for i in range(6)]
TIME_SLOTS = generate_course_schedule()
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def generate_takes(df_students, df_courses, homerooms):
    takes = []
    schedule_map = {}
    time_slots = generate_course_schedule()

    for school_id in homerooms:
        for grade in homerooms[school_id]:
            for homeroom_id, h_data in homerooms[school_id][grade].items():
                courses = df_courses.sample(6, random_state=random.randint(0, 10000))["course_id"].tolist()
                schedule_map[(school_id, grade, homeroom_id)] = courses
                for student_id in h_data["students"]:
                    for i, course_id in enumerate(courses):
                        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
                            takes.append({
                                "student_id": student_id,
                                "course_id": course_id,
                                "day": day,
                                "start_time": time_slots[i]["start_time"],
                                "end_time": time_slots[i]["end_time"]
                            })
    return pd.DataFrame(takes), schedule_map


def generate_teaches(df_teachers, df_students, df_takes, schedule_map, homerooms):
    teaches = []
    assigned_slots = {}  # teacher_id -> {day -> set of (start_time)}

    time_slots = generate_course_schedule()

    for key, course_ids in schedule_map.items():
        school_id, grade, homeroom_id = key
        h_teacher_id = homerooms[school_id][grade][homeroom_id]["teacher_id"]

        for i, course_id in enumerate(course_ids):
            slot = time_slots[i]
            start_time = slot["start_time"]
            end_time = slot["end_time"]

            # Determine who will teach this course
            teacher_id = None
            candidates = []

            if school_id in [1, 2, 3, 4]:  # Elementary: only homeroom teacher
                candidates = [h_teacher_id]
            else:
                candidates = [h_teacher_id] if random.random() < 0.5 else df_teachers[df_teachers["school_id"] == school_id]["teacher_id"].tolist()

            # Shuffle candidates for fairness
            random.shuffle(candidates)

            # Try to assign a teacher without time conflict
            for candidate in candidates:
                has_conflict = any(
                    start_time in assigned_slots.get(candidate, {}).get(day, set())
                    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                )
                if not has_conflict:
                    teacher_id = candidate
                    break

            # If all candidates conflict, skip assigning this course
            if teacher_id is None:
                continue

            # Mark time as assigned for this teacher
            if teacher_id not in assigned_slots:
                assigned_slots[teacher_id] = {day: set() for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]}

            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
                assigned_slots[teacher_id][day].add(start_time)
                teaches.append({
                    "teacher_id": teacher_id,
                    "course_id": course_id,
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "homeroom_id": homeroom_id,
                    "school_id": school_id,
                    "grade_level": grade
                })

    return pd.DataFrame(teaches)


##### Generate Attendance Data #####
def generate_attendance_data(df_students, start_date='2025-03-15', end_date='2025-05-15'):
    """
    Generate attendance records for students during Spring 2025 semester
    """
    attendance = []
    attendance_id = 1
    
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Generate all school days (Monday-Friday, excluding holidays)
    school_days = []
    current_date = start_date
    
    # List of major holidays/breaks during Spring 2025
    holidays = [
        # '2025-01-20',  # MLK Day
        # '2025-02-17',  # Presidents Day
        '2025-03-24',  # Spring break start
        '2025-03-28',  # Spring break end
        '2025-04-18'  # Good Friday
    ]
    holidays = [datetime.strptime(d, '%Y-%m-%d').date() for d in holidays]
    
    while current_date <= end_date:
        if current_date.weekday() < 5 and current_date not in holidays:
            school_days.append(current_date)
        current_date += timedelta(days=1)
    
    # Create a mapping of school_id to available teachers for fallback
    school_teachers = df_students.groupby('school_id')['homeroom_teacher_id'].unique().to_dict()
    
    for _, student in df_students.iterrows():
        student_id = student['student_id']
        school_id = student['school_id']
        homeroom_teacher = student['homeroom_teacher_id']
        
        # Get fallback teachers for this school if needed
        available_teachers = school_teachers.get(school_id, [])
        
        # Attendance patterns - elementary students have better attendance
        grade = student['grade_level']
        if grade in ['K', '1', '2', '3', '4', '5']:
            base_absence_prob = 0.04  # Elementary
        elif grade in ['6', '7', '8']:
            base_absence_prob = 0.06  # Middle school
        else:
            base_absence_prob = 0.07  # High school
            
        if school_id == 10:  # Special ed
            base_absence_prob = 0.09
        
        consecutive_absences = 0
        
        for day in school_days:
            status = 'present'
            
            # Skip attendance for weekends/holidays (shouldn't happen but just in case)
            if day.weekday() >= 5 or day in holidays:
                continue
                
            # Random chance of absence
            if random.random() < base_absence_prob:
                status = 'absent'
                consecutive_absences += 1
                
                # Higher chance of continuing absence (illness)
                if consecutive_absences > 0 and random.random() < 0.6:
                    status = 'absent'
                    consecutive_absences += 1
                else:
                    consecutive_absences = 0
                    
                # Convert some absences to late/excused
                if status == 'absent' and random.random() < 0.3:
                    status = 'late' if random.random() < 0.7 else 'excused'
            else:
                consecutive_absences = 0
            
            # Determine recorded_by - use homeroom teacher if available, otherwise random teacher from same school
            if pd.notna(homeroom_teacher):
                recorded_by = homeroom_teacher
            elif available_teachers:
                recorded_by = random.choice(available_teachers)
            else:
                recorded_by = random.randint(1000, 2000)  # Fallback admin ID range
            
            # Add notes for non-present records (15% chance)
            notes = None
            if status != 'present' and random.random() < 0.15:
                reasons = {
                    'absent': ["Illness", "Family emergency", "Doctor appointment"],
                    'late': ["Traffic", "Overslept", "Transportation issue"],
                    'excused': ["School activity", "Religious holiday", "College visit"]
                }
                notes = random.choice(reasons[status])
            
            attendance.append({
                'attendance_id': attendance_id,
                'student_id': student_id,
                'date': day.strftime('%Y-%m-%d'),
                'status': status,
                'recorded_by': recorded_by,
                'notes': notes
            })
            attendance_id += 1
    
    return pd.DataFrame(attendance)


def generate_grade_details(df_takes):
    """
    Generate detailed grade entries per student-course based on predefined grade types.
    """
    grade_types = {
        'homework': {
            'count': 2,    
            'weight': 0.05, 
            'score_mean': 85,
            'score_std': 12
        },
        'quiz': {
            'count': 1,
            'weight': 0.2,
            'score_mean': 82,
            'score_std': 15
        },
        'mid exam': {
            'count': 1,
            'weight': 0.3,
            'score_mean': 78,
            'score_std': 17
        },
        'final exam': {
            'count': 1,
            'weight': 0.4,
            'score_mean': 76,
            'score_std': 18
        }
    }

    # Unique student-course combinations only
    unique_pairs = df_takes[['student_id', 'course_id']].drop_duplicates()
    grade_details = []

    for _, row in unique_pairs.iterrows():
        student_id = row["student_id"]
        course_id = row["course_id"]

        for grade_type, config in grade_types.items():
            for idx in range(config['count']):
                score = round(random.gauss(config['score_mean'], config['score_std']))
                score = max(20, min(score, 100)) 

                if config['count'] > 1:
                    grade_type_name = f"{grade_type}{idx + 1}"
                else:
                    grade_type_name = grade_type

                grade_details.append({
                    "student_id": student_id,
                    "course_id": course_id,
                    "grade_type": grade_type_name,
                    "score": score,
                    "weight": config['weight']
                })

    return pd.DataFrame(grade_details)


def main():
    # Generate user data
    print("Generating user data...")
    df_users, all_names = generate_users()
    save_data(df_users)

    # Generate district data
    print("\nGenerating district data...")
    df_districts = generate_districts(superintendent_id=1)
    df_districts.to_csv("districts_data.csv", index=False)

    # Generate school data
    print("\nGenerating school data...")
    df_schools = generate_schools(district_id=1, num_schools=10)
    df_schools.to_csv("schools_data.csv", index=False)

    # Generate guardian data
    print("\nGenerating guardian data...")
    df_guardians = generate_guardians(df_users, all_names)
    df_guardians.to_csv("guardians_data.csv", index=False)

    # Generate teacher data
    print("\nGenerating teacher data...")
    school_ids = df_schools["school_id"].tolist()
    df_teachers = generate_teachers(df_users, all_names, school_ids)
    df_teachers.to_csv("teachers_data.csv", index=False)

    # Generate student data
    print("\nGenerating student data...")
    df_students, homerooms = generate_students(df_users, all_names, df_teachers)
    df_students.to_csv("students_data.csv", index=False)

    # Generate guardian-student relationships
    print("\nGenerating guardian-student relationships...")
    df_relationships = generate_guardian_student_relationships(df_students, df_guardians)
    df_relationships.to_csv("guardian_student_relationships.csv", index=False)

    # Generate admin data
    print("\nGenerating admin data...")
    df_admins = generate_admins(df_users, all_names, df_schools)
    df_admins.to_csv("admins_data.csv", index=False)
    
    # Generate course data
    print("\nGenerating course data...")
    df_courses = generate_courses()
    df_courses.to_csv("school_courses.csv", index=False)

    # Generate takes data
    print("\nGenerating takes data...")
    df_takes, schedule_map = generate_takes(df_students, df_courses, homerooms)
    df_takes.to_csv("takes_data.csv", index=False)

    # Generate teaches data
    print("\nGenerating teaches data...")
    df_teaches = generate_teaches(df_teachers, df_students, df_takes, schedule_map, homerooms)
    df_teaches.to_csv("teaches_data.csv", index=False)

    # Generate attendance data
    print("\nGenerating attendance data...")
    df_attendance = generate_attendance_data(df_students)
    df_attendance.to_csv("attendance_data.csv", index=False)

    # Generate grade details
    print("\nGenerating grade details...")
    df_grade_details = generate_grade_details(df_takes)
    df_grade_details.to_csv("grade_details.csv", index=False)


if __name__ == "__main__":
    main()
