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
        'teacher': 150, #200
        'student': 2000, #300
        'guardian': 3000, #5000
        'school_admin': 14, #20
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


def generate_students(user_df, all_names, df_teachers, num_student=2000):
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
    
    return pd.DataFrame(students)


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


def generate_schools(num_schools=7, district_id=1, principal_ids=None):
    """ Generate school data linked to districts and admins """
    schools = []
    school_id = 1

    # Elementary Schools (2)
    for i in range(2):
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
    
    # Middle Sschools (2)
    for i in range(2):
        schools.append({
            "school_id": school_id,
            "district_id": district_id,
            "name": f"{fake.last_name()} Middle School",
            "school_type": "middle",
            "address": fake.street_address(),
            "city": "San Jose",
            "state": "CA",
            "zip": random.randint(95002, 95196),
            "principal_id": i+3
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
            "principal_id": i+5
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
        "principal_id": 7
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

# def generate_course_schedule(school_type):
#         if school_type == "Elementary":
#             return [
#                 {"start_time": "8:00", "end_time": "8:45"},
#                 {"start_time": "8:50", "end_time": "9:35"},
#                 {"start_time": "9:40", "end_time": "10:25"},
#                 {"start_time": "10:30", "end_time": "11:15"},
#                 {"start_time": "11:20", "end_time": "12:05"},
#                 {"start_time": "12:50", "end_time": "1:35"},
#                 {"start_time": "1:40", "end_time": "2:25"}
#             ]
#         elif school_type == "Middle":
#             return [
#                 {"start_time": "8:00", "end_time": "8:50"},
#                 {"start_time": "8:55", "end_time": "9:45"},
#                 {"start_time": "9:50", "end_time": "10:40"},
#                 {"start_time": "10:45", "end_time": "11:35"},
#                 {"start_time": "11:40", "end_time": "12:30"},
#                 {"start_time": "12:50", "end_time": "1:40"},
#                 {"start_time": "1:45", "end_time": "2:35"}
#             ]
#         elif school_type == "High" or school_type == "SpecialEd":
#             return [
#                 {"start_time": "8:00", "end_time": "8:50"},
#                 {"start_time": "8:55", "end_time": "9:45"},
#                 {"start_time": "9:50", "end_time": "10:40"},
#                 {"start_time": "10:45", "end_time": "11:35"},
#                 {"start_time": "11:40", "end_time": "12:30"},
#                 {"start_time": "12:50", "end_time": "1:40"},
#                 {"start_time": "1:45", "end_time": "2:35"},
#                 {"start_time": "2:40", "end_time": "3:30"}  
#             ]
        
def generate_course_schedule():
    return [
        {"start_time": "8:30", "end_time": "9:15"},  
        {"start_time": "9:25", "end_time": "10:10"},  
        {"start_time": "10:20", "end_time": "11:05"},  
        {"start_time": "11:15", "end_time": "12:00"},  
        {"start_time": "1:00", "end_time": "1:50"},  
        {"start_time": "2:00", "end_time": "2:45"}   
    ]


def generate_courses(n=176):
    """ Generate course data """  
    courses = []
    used_codes = set()  # Track unique (school_id, subject, course_code) combinations
    used_course_names = set()  # Track unique (school_id, subject, course_name) combinations

    # Create a mapping from school_id to school_type
    school_type_map = {}
    for school_id in range(1, 5):  # 1-4 Elementary
        school_type_map[school_id] = "Elementary"
    for school_id in range(5, 8):  # 5-7 Middle
        school_type_map[school_id] = "Middle"
    for school_id in range(8, 10):  # 8-9 High
        school_type_map[school_id] = "High"
    school_type_map[10] = "SpecialEd"  # 10 SpecialEd

    

    # Generate period schedules for each school
    school_periods = {}
    for school_id, school_type in school_type_map.items():
        school_periods[school_id] = generate_course_schedule()

    # Weekdays
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Define subject codes and course names mapping (by education level)
    subject_courses = {
    "Elementary": {
        "ELA": [
            "Reading Basics", "Creative Writing for Kids", "Phonics and Spelling", "Storytelling Adventures", "Reading Comprehension",
            "Building Vocabulary", "Poetry for Children", "Writing Sentences", "Reading Aloud Practice", "Language Games"
        ],
        "MATH": [
            "Addition and Subtraction", "Shapes and Patterns", "Introduction to Fractions", "Math Through Games", "Problem Solving Skills",
            "Telling Time", "Counting Money", "Multiplication Fun", "Math with Manipulatives", "Graphing for Beginners"
        ],
        "SCI": [
            "Exploring Nature", "Simple Machines", "Weather and Seasons", "Astronomy for Kids",
            "Animal Habitats", "Plant Life Cycle", "States of Matter", "The Five Senses", "Water Cycle Wonders", "Introduction to Energy"
        ],
        "HIST": [
            "Community and Helpers", "California's Story", "Symbols of America", "Discovering World Cultures",
            "Native American Tales", "Important Inventors", "Timelines and History", "Then and Now", "Presidents and Patriots", "Mapping Our World"
        ],
        "PE": [
            "Fun Fitness", "Healthy Habits", "Basic Gymnastics", "Team Play",
            "Movement and Music", "Balance and Coordination", "Yoga for Kids", "Playground Games", "Obstacle Course Fun", "Stretching Routines"
        ],
        "ART": [
            "Creative Drawing", "Music Exploration", "Handmade Crafts",
            "Painting with Nature", "Puppet Making", "Color and Shapes", "Clay Creations", "Paper Art", "Collage Fun", "Sing and Play"
        ],
        "STEAM": [
            "Building and Design", "Robotics for Beginners", "Coding Through Play",
            "Simple Circuits", "Marble Run Engineering", "Weather Science Projects", "Design a Bridge", "Math in Art", "3D Shapes in Real Life", "Tech Tools for Kids"
        ]
    },
    "Middle": {
        "ELA": [
            "Exploring Literature", "Creative Writing Projects", "Debate and Public Speaking", "Critical Reading Skills",
            "Poetry and Prose", "Literary Elements", "Argument Writing", "Mythology and Legends", "Nonfiction Analysis", "Collaborative Writing"
        ],
        "MATH": [
            "Foundations of Algebra", "Geometry in Action", "Practical Math Applications", "Problem Solving and Logic",
            "Pre-Algebra Skills", "Graphing and Coordinates", "Ratios and Proportions", "Integers and Operations", "Math Games and Puzzles", "Data and Probability"
        ],
        "SCI": [
            "Life and Ecosystems", "Earth's Processes", "Physics in Everyday Life", "The Wonders of Space",
            "Human Body Systems", "Energy and Forces", "Scientific Investigations", "Cells and Genetics", "Climate Change", "Chemical Interactions"
        ],
        "HIST": [
            "Civilizations of the Past", "America's Journey", "Geography and Cultures", "Medieval Times",
            "World Religions", "Exploration and Discovery", "Revolutions in History", "Ancient Governments", "Trade and Economy", "Understanding Maps"
        ],
        "PE": [
            "Active Lifestyles", "Sports and Teamwork", "Strength and Conditioning",
            "Cardio Fitness", "Dance and Movement", "Wellness and Nutrition", "Self-Defense Basics", "Stretching and Flexibility", "Mind-Body Balance", "Track and Field"
        ],
        "SPAN": [
            "Introduction to Spanish", "Spanish Communication", "Hispanic Cultures",
            "Spanish Songs and Stories", "Basic Spanish Grammar", "Spanish for Travel", "Spanish Vocabulary Builder", "Everyday Spanish Phrases", "Latin American Geography", "Bilingual Games"
        ],
        "ART": [
            "Digital Art Techniques", "Basics of Photography", "Music and Sound Creation",
            "Visual Storytelling", "Sketching for Beginners", "Art History Exploration", "Stop Motion Animation", "Instrument Basics", "Creative Collage", "Performance Art"
        ],
        "STEAM": [
            "Design with Technology", "Introduction to Robotics", "Game Development Basics",
            "3D Printing Projects", "Science Fair Innovations", "Engineering Design Challenges", "Circuitry and Coding", "Drone Exploration", "Animation Tools", "Sustainable Design"
        ],
        "Electives": [
            "Theater and Performance", "Cooking and Nutrition", "Gardening for Beginners",
            "Yearbook and Media", "Student Leadership", "Basic Carpentry", "Photography Club", "Chess Strategies", "Creative Journaling", "Animal Care"
        ]
    },
    "High": {
        "ENG": [
            "Literary Analysis", "Creative Writing and Poetry", "Journalism and Media Studies",
            "Shakespeare and Drama", "World Literature", "Research Writing", "Modern Fiction", "Argument and Persuasion", "Speech Writing", "Rhetorical Techniques"
        ],
        "MATH": [
            "Advanced Algebra", "Exploring Calculus", "Statistics and Data Analysis", "Mathematical Problem Solving",
            "Geometry and Proofs", "Trigonometry", "Financial Mathematics", "Logic and Reasoning", "Applied Math Projects", "Discrete Mathematics"
        ],
        "SCI": [
            "Biological Systems", "Chemical Reactions", "Physics Principles", "Environmental Challenges",
            "Genetics and Evolution", "Astronomy and Space", "Forensic Science", "Marine Biology", "Scientific Research Methods", "Renewable Energy Systems"
        ],
        "HIST": [
            "Global Perspectives", "Government and Democracy", "Economics and Society", "Human Geography",
            "World Wars and Conflict", "American History Since 1900", "Cultural Anthropology", "Political Theory", "Social Justice Movements", "International Relations"
        ],
        "PE": [
            "Personal Fitness", "Yoga and Mindfulness", "Strength Training",
            "Team Sports", "Aerobic Conditioning", "Sports Science", "Injury Prevention", "Recreational Activities", "Outdoor Education", "Health and Wellness"
        ],
        "CS": [
            "Programming Fundamentals", "Advanced Computing Concepts", "Web and App Design",
            "Data Structures", "Game Programming", "Cybersecurity Basics", "Intro to AI", "Mobile Development", "UI/UX Design", "Cloud Technology Overview"
        ],
        "ART": [
            "Mastering Drawing", "Digital Media Arts", "Music Production",
            "Advanced Painting", "Graphic Design", "Photography and Editing", "Theater Arts", "Sculpture Studio", "Film Making", "Songwriting and Composition"
        ],
        "STEAM": [
            "Artificial Intelligence Basics", "Innovations in Robotics", "Mobile App Development",
            "3D Modeling and Printing", "Engineering Challenges", "Scientific Computing", "Biotech Explorations", "Virtual Reality Design", "Green Tech Projects", "Design Thinking Studio"
        ],
        "Electives": [
            "Public Speaking and Leadership", "Film and Media Studies", "Entrepreneurship and Business",
            "Creative Entrepreneurship", "Social Media Strategy", "Psychology Basics", "Philosophy and Ethics", "Career Readiness", "Community Service", "Debate and Diplomacy"
        ]
    },
    "SpecialEd": {
        "LIFE": [
            "Practical Life Skills", "Building Social Connections", "Independent Living Skills",
            "Time Management", "Personal Hygiene", "Navigating the Community", "Daily Routines", "Safe Decision Making", "Shopping and Budgeting", "Workplace Readiness"
        ],
        "MATH": [
            "Everyday Math", "Managing Money", "Understanding Numbers",
            "Counting in Context", "Time and Schedules", "Measurement Basics", "Shopping Math", "Math Games", "Basic Geometry", "Simple Graphs"
        ],
        "ELA": [
            "Reading for Confidence", "Expressive Writing", "Communication Skills",
            "Sight Word Practice", "Listening Comprehension", "Sentence Building", "Interactive Stories", "Story Sequencing", "Functional Reading", "Reading Aloud Practice"
        ],
        "OT": [
            "Fine Motor Development", "Occupational Therapy Activities",
            "Sensory Integration", "Handwriting Practice", "Self-Care Routines", "Movement and Coordination", "Grasp and Release Skills", "Tactile Exploration", "Visual Motor Skills", "Adaptive Tools Training"
        ],
        "SEL": [
            "Building Emotional Resilience", "Managing Conflict", "Mindfulness Practices",
            "Friendship Skills", "Recognizing Emotions", "Coping Strategies", "Making Good Choices", "Social Stories", "Emotional Check-Ins", "Teamwork Activities"
        ],
        "Electives": [
            "Art for Expression", "Music for Relaxation", "Sensory Exploration",
            "Dance and Movement", "Drama Games", "Interactive Technology", "Story Songs", "Gardening Therapy", "Animal Interaction", "Crafting with Purpose"]
        }
    }

    school_course_schedules = {school_id: {} for school_id in school_type_map.keys()}

    used_subject_course_names = {}

    attempts = 0
    max_attempts = n * 10  

    while len(courses) < n and attempts < max_attempts:
        attempts += 1
        
        # Select a school_id to ensure we get the right school_type
        school_id = random.choice(list(school_type_map.keys()))
        school_type = school_type_map[school_id]

        # Select subject based on school_type
        subject = random.choice(list(subject_courses[school_type].keys()))
        
        # Initialize tracking for this school+subject if not exists
        if (school_id, subject) not in used_subject_course_names:
            used_subject_course_names[(school_id, subject)] = set()
        
        # Get available course names for this school and subject
        available_course_names = [
            name for name in subject_courses[school_type][subject]
            if name not in used_subject_course_names[(school_id, subject)]
        ]
        
        # If no more course names available for this subject at this school, skip
        if not available_course_names:
            continue
            
        # Select an unused course name
        course_name = random.choice(available_course_names)
        
        # Generate course code
        course_code = f"{random.randint(100, 299)}"

        # Check if this combination is already used
        combination_key = f"{school_id}_{subject}_{course_code}"
        if combination_key in used_codes:
            continue
            
        # Mark this combination as used
        used_codes.add(combination_key)
        used_subject_course_names[(school_id, subject)].add(course_name)

        # Initialize subject schedule if not exists
        if subject not in school_course_schedules[school_id]:
            school_course_schedules[school_id][subject] = {day: set() for day in weekdays}

        # Target grade level
        if school_type == "SpecialEd":
            target_grade = "K-12"
        elif school_type == "Elementary":
            target_grade = random.choice(["K-2", "3-5"])
        elif school_type == "Middle":
            target_grade = random.choice(["6-8"])
        else:
            target_grade = random.choice(["9-10", "11-12"])

        # For core subjects (ELA, MATH, SCI, HIST), schedule multiple times per week
        # For electives, schedule 1-2 times per week
        is_core = subject in ["ELA", "MATH", "SCI", "HIST", "ENG"]

        # Determine how many days per week this course meets
        if is_core:
            sessions_per_week = random.randint(2, 4)  # Core subjects meet 2-4 times per week
        else:
            sessions_per_week = random.randint(1, 2)  # Electives meet 1-2 times per week

        # Select random weekdays for this course
        course_days = random.sample(weekdays, min(sessions_per_week, len(weekdays)))

        # For each selected day, assign a period
        schedule = []
        valid_schedule = True

        for day in course_days:
            # Get all periods for this school
            all_periods = list(range(1, len(school_periods[school_id]) + 1))

            # Remove periods already used by this subject on other days
            used_periods = set()
            for other_day in school_course_schedules[school_id][subject]:
                used_periods.update(school_course_schedules[school_id][subject][other_day])

            # Try to find an available period
            available_periods = [p for p in all_periods if p not in used_periods]

            if not available_periods:
                # If no periods available, try the next subject
                valid_schedule = False
                break
    
            # Select a random period
            selected_period = random.choice(available_periods)

            # Record this period as used for this subject on this day
            school_course_schedules[school_id][subject][day].add(selected_period)

            # Get the actual time slot
            period_info = school_periods[school_id][selected_period - 1]

            # Add to schedule
            schedule.append({
                "day": day,
                "period": selected_period,
                "start_time": period_info["start_time"],
                "end_time": period_info["end_time"]
            })

        if not valid_schedule or not schedule:
            continue

        # Create the time_slot string
        time_slot_parts = []
        for session in schedule:
            time_slot_parts.append(f"{session['day']} P{session['period']} ({session['start_time']}-{session['end_time']})")

        time_slot = "; ".join(time_slot_parts)

        # Add to courses list
        courses.append({
            "subject_code": subject,
            "course_code": course_code,
            "school_id": school_id,  
            "course_name": course_name,
            "target_grade_level": target_grade,
            "description": f"This course covers {course_name.lower()} for {target_grade} students.",
            "time_slot": time_slot,
            "schedule": schedule, 
            "semester": "Spring2025"
        })

    # If we couldn't generate enough courses with our constraints
    if len(courses) < n:
        print(f"Warning: Could only generate {len(courses)} courses with the given constraints instead of the requested {n}.")

    return pd.DataFrame(courses)

##### Generate Teaches Data #####
# def generate_teaches_data(df_courses, df_teachers, n=200):
#     """ Generate teaches data linking teachers to courses """
#     teaches = []

#     valid_combinations = {}
#     for _, teacher in df_teachers.iterrows():
#         school_id = teacher['school_id']
        
#         matching_courses = df_courses[(df_courses['school_id'] == school_id)]
#         if not matching_courses.empty:
#             valid_combinations[teacher['teacher_id']] = {
#                 'school_id': school_id,
#                 'available_courses': matching_courses[['course_code', 'subject_code']].to_dict('records')
#             }
#     for _ in range(n):
#         if not valid_combinations:
#             break

#         teacher_id = random.choice(list(valid_combinations.keys()))
#         teacher_info = valid_combinations[teacher_id]

#         if not teacher_info['available_courses']:
#             del valid_combinations[teacher_id] 
#             continue
        
#         # Select random course
#         course = random.choice(teacher_info['available_courses'])
        
#         teaches.append({
#             'teacher_id': teacher_id,
#             'subject_code': course['subject_code'],
#             'course_code': course['course_code'],
#             'school_id': teacher_info['school_id']
#         })
        
#         # Remove this course to avoid duplicate assignments
#         teacher_info['available_courses'].remove(course)
    
#     return pd.DataFrame(teaches)

def generate_teaches_data(df_courses, df_teachers, df_students, n=100000):
    """Generate teaches data linking teachers to courses based on homeroom_teacher_id for students."""
    teaches = []
    
    # Create a mapping from school_id to homeroom teachers and students
    homeroom_teachers = {}
    school_students = {}
    
    for _, teacher in df_teachers.iterrows():
        school_id = teacher['school_id']
        if school_id not in homeroom_teachers:
            homeroom_teachers[school_id] = []
        homeroom_teachers[school_id].append(teacher)
    
    # Create student to homeroom_teacher_id mapping for each school
    for _, student in df_students.iterrows():
        school_id = student['school_id']
        if school_id not in school_students:
            school_students[school_id] = []
        school_students[school_id].append(student)
    
    # For elementary schools, homeroom teacher teaches all courses for the homeroom
    for school_id, students in school_students.items():
        school_courses = df_courses[df_courses['school_id'] == school_id]

        if school_id <= 4:  # Elementary schools
            for student in students:
                homeroom_teacher_id = student['homeroom_teacher_id']
                for _, course in school_courses.iterrows():
                    teaches.append({
                        'teacher_id': homeroom_teacher_id,
                        'subject_code': course['subject_code'],
                        'course_code': course['course_code'],
                        'school_id': school_id
                    })
        else:  # Middle, High, and SpecialEd
            # For each student, assign a homeroom teacher for one course (as homeroom teacher)
            for student in students:
                homeroom_teacher_id = student['homeroom_teacher_id']
                homeroom_course = random.choice(school_courses[['course_code', 'subject_code']].to_dict('records'))
                teaches.append({
                    'teacher_id': homeroom_teacher_id,
                    'subject_code': homeroom_course['subject_code'],
                    'course_code': homeroom_course['course_code'],
                    'school_id': school_id
                })

                # Assign the rest of the courses to this homeroom teacher for other classes they are not homeroom teacher
                remaining_courses = school_courses[school_courses['course_code'] != homeroom_course['course_code']]
                available_teachers = [t['teacher_id'] for t in homeroom_teachers[school_id] if t['teacher_id'] != homeroom_teacher_id]
                
                # Homeroom teacher can teach other classes but not as homeroom teacher
                for _, course in remaining_courses.iterrows():
                    assigned_teacher = random.choice(available_teachers)
                    teaches.append({
                        'teacher_id': assigned_teacher,
                        'subject_code': course['subject_code'],
                        'course_code': course['course_code'],
                        'school_id': school_id
                    })

                # Assign other teachers for the remaining courses for other classes
                for _, course in remaining_courses.iterrows():
                    other_teacher = random.choice([t['teacher_id'] for t in homeroom_teachers[school_id] if t['teacher_id'] != homeroom_teacher_id])
                    teaches.append({
                        'teacher_id': other_teacher,
                        'subject_code': course['subject_code'],
                        'course_code': course['course_code'],
                        'school_id': school_id
                    })
    
    # If we reach the limit of n records, stop generating
    if len(teaches) > n:
        teaches = teaches[:n]
    
    return pd.DataFrame(teaches)


# ##### Generate Takes Data #####
# def generate_takes_data(df_students, df_courses):
#     takes = []
#     enrollment_id = 1
    
#     # Define core subjects by school level
#     ELEMENTARY_CORE = ['ELA', 'MATH', 'SCI', 'HIST']
#     MIDDLE_CORE = ['ELA', 'MATH', 'SCI', 'HIST']
#     HIGH_CORE = ['ENG', 'MATH', 'SCI', 'HIST']
#     SPECIAL_CORE = ['LIFE', 'MATH', 'ELA', 'SEL']
    
#     # Weekdays
#     weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
#     def is_grade_in_range(grade, target_grade):
#         """Check if a single grade falls within a target grade range"""
#         if target_grade == "K-12":
#             return True
#         if grade == "K":
#             return "K" in target_grade
#         if "-" in target_grade:
#             start, end = target_grade.split("-")
#             if grade.isdigit() and start.isdigit() and end.isdigit():
#                 return int(start) <= int(grade) <= int(end)
#             # Handle cases like "K-2"
#             if start == "K" and grade == "K":
#                 return True
#             if start == "K" and grade.isdigit():
#                 return int(grade) <= int(end)
#         return grade == target_grade
    
#     # Process each student to create a complete weekly schedule
#     for _, student in df_students.iterrows():
#         student_id = student['student_id']
#         school_id = student['school_id']
#         grade_level = student['grade_level']
        
#         # Determine school type and core subjects
#         if school_id <= 4:  # Elementary
#             school_type = "Elementary"
#             core_subjects = ELEMENTARY_CORE
#             max_periods = 8  # Elementary schools have 8 periods
#         elif school_id <= 7:  # Middle
#             school_type = "Middle"
#             core_subjects = MIDDLE_CORE
#             max_periods = 8  # Middle schools have 8 periods
#         elif school_id <= 9:  # High
#             school_type = "High"
#             core_subjects = HIGH_CORE
#             max_periods = 8  # High schools have 8 periods
#         else:  # Special Ed
#             school_type = "SpecialEd"
#             core_subjects = SPECIAL_CORE
#             max_periods = 8  # Special Ed schools have 8 periods
        
#         # Filter courses for this student's school and grade
#         eligible_courses = []
#         for _, course in df_courses[df_courses['school_id'] == school_id].iterrows():
#             if is_grade_in_range(grade_level, course['target_grade_level']):
#                 eligible_courses.append(course.to_dict())
        
#         if not eligible_courses:
#             continue  # No eligible courses for this student
        
#         # Get period data for this school - Uses the global generate_course_schedule function
#         period_data = generate_course_schedule(school_type)
        
#         # Initialize student schedule: {day: {period: course}}
#         student_schedule = {day: {} for day in weekdays}
        
#         # Track assigned course codes for specific handling
#         assigned_course_codes = set()
        
#         # Step 1: First assign core courses with fixed periods across multiple days
#         for core_subject in core_subjects:
#             # Find courses for this core subject
#             core_options = [c for c in eligible_courses 
#                            if c['subject_code'] == core_subject]
            
#             if not core_options:
#                 continue  # No courses for this core subject
            
#             # Pick a random core course
#             selected_core = random.choice(core_options)
#             assigned_course_codes.add(selected_core['course_code'])
            
#             # Core subjects appear on 3-5 days per week
#             days_per_week = random.randint(3, 5)
#             course_days = random.sample(weekdays, days_per_week)
            
#             # Find an available period that works across all selected days
#             available_periods = list(range(1, max_periods + 1))
#             random.shuffle(available_periods)  # Randomize period order
            
#             for period in available_periods:
#                 # Check if this period works for all selected days
#                 valid_for_all_days = True
#                 for day in course_days:
#                     if period in student_schedule[day]:
#                         valid_for_all_days = False
#                         break
                
#                 if valid_for_all_days:
#                     # Assign this course to this period on all selected days
#                     for day in course_days:
#                         # Get period time data
#                         period_time = period_data[period - 1]
                        
#                         student_schedule[day][period] = {
#                             'course': selected_core,
#                             'start_time': period_time['start_time'],
#                             'end_time': period_time['end_time']
#                         }
#                     break
        
#         # Step 2: Create a pool of electives for each student
#         elective_options = [c for c in eligible_courses 
#                          if c['subject_code'] not in core_subjects 
#                          and c['course_code'] not in assigned_course_codes]
        
#         # If we don't have enough electives, allow repeating core subjects
#         if len(elective_options) < 20:  # Ensure we have enough variety
#             additional_options = [c for c in eligible_courses 
#                               if c['course_code'] not in assigned_course_codes]
#             elective_options.extend(additional_options)
        
#         # Step 3: Fill each day to exactly 7 classes
#         for day in weekdays:
#             # How many classes already assigned for this day?
#             current_classes = len(student_schedule[day])
            
#             # How many more classes needed to reach exactly 7?
#             needed_classes = 7 - current_classes
            
#             if needed_classes <= 0:
#                 continue  # Already have at least 7 classes
            
#             # Find periods that need to be filled
#             assigned_periods = set(student_schedule[day].keys())
#             available_periods = sorted(list(set(range(1, max_periods + 1)) - assigned_periods))
            
#             # Subjects already assigned today
#             assigned_subjects_today = set([student_schedule[day][p]['course']['subject_code'] 
#                                     for p in student_schedule[day]])
            
#             # Fill exactly needed_classes periods
#             for _ in range(needed_classes):
#                 if not available_periods:
#                     break  # Shouldn't happen if max_periods >= 7
                
#                 period = available_periods.pop(0)
                
#                 # Prioritize courses with different subjects than already assigned today
#                 preferred_options = [e for e in elective_options 
#                                   if e['subject_code'] not in assigned_subjects_today]
                
#                 if not preferred_options:
#                     preferred_options = elective_options  # Fallback to any available elective
                
#                 if not preferred_options:
#                     # Final fallback: use any eligible course (could repeat)
#                     preferred_options = eligible_courses
                
#                 # Select a course
#                 if preferred_options:
#                     selected_course = random.choice(preferred_options)
                    
#                     # Get period time data
#                     period_time = period_data[period - 1]
                    
#                     # Assign to schedule
#                     student_schedule[day][period] = {
#                         'course': selected_course,
#                         'start_time': period_time['start_time'],
#                         'end_time': period_time['end_time']
#                     }
                    
#                     # Update tracking
#                     assigned_subjects_today.add(selected_course['subject_code'])
                    
#                     # Remove from options if not a fallback
#                     if selected_course in elective_options:
#                         elective_options.remove(selected_course)
        
#         # Step 4: Create final enrollment records
#         for day in weekdays:
#             # Verify we have exactly 7 classes scheduled
#             if len(student_schedule[day]) != 7:
#                 # If we still don't have exactly 7, add or remove as needed
#                 # This is a fallback and shouldn't normally happen
#                 assigned_periods = sorted(list(student_schedule[day].keys()))
                
#                 if len(assigned_periods) < 7:
#                     # Need to add more periods
#                     available_periods = sorted(list(set(range(1, max_periods + 1)) - 
#                                             set(assigned_periods)))
                    
#                     while len(student_schedule[day]) < 7 and available_periods:
#                         period = available_periods.pop(0)
                        
#                         # Pick any course
#                         selected_course = random.choice(eligible_courses)
#                         period_time = period_data[period - 1]
                        
#                         student_schedule[day][period] = {
#                             'course': selected_course,
#                             'start_time': period_time['start_time'],
#                             'end_time': period_time['end_time']
#                         }
                
#                 elif len(assigned_periods) > 7:
#                     # Need to remove periods to get exactly 7
#                     # Remove from the end of the day
#                     periods_to_remove = len(assigned_periods) - 7
#                     for _ in range(periods_to_remove):
#                         period_to_remove = max(assigned_periods)
#                         del student_schedule[day][period_to_remove]
#                         assigned_periods.remove(period_to_remove)
            
#             # Create entries for this day
#             for period in student_schedule[day]:
#                 course_data = student_schedule[day][period]
#                 course = course_data['course']
                
#                 # Create enrollment record
#                 takes.append({
#                     'enrollment_id': enrollment_id,
#                     'student_id': student_id,
#                     'subject_code': course['subject_code'],
#                     'course_code': course['course_code'],
#                     'semester': course['semester'],
#                     'school_id': school_id,
#                     'is_core': course['subject_code'] in core_subjects,
#                     'weekday': day,
#                     'period': period,
#                     'start_time': course_data['start_time'],
#                     'end_time': course_data['end_time']
#                 })
#                 enrollment_id += 1
    
#     return pd.DataFrame(takes)

def generate_takes_data(df_students, df_courses):
    takes = []
    enrollment_id = 1

    # Define core subjects by school level
    ELEMENTARY_CORE = ['ELA', 'MATH', 'SCI', 'HIST']
    MIDDLE_CORE = ['ELA', 'MATH', 'SCI', 'HIST']
    HIGH_CORE = ['ENG', 'MATH', 'SCI', 'HIST']
    SPECIAL_CORE = ['LIFE', 'MATH', 'ELA', 'SEL']

    # Weekdays
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    def is_grade_in_range(grade, target_grade):
        """Check if a single grade falls within a target grade range"""
        if target_grade == "K-12":
            return True
        if grade == "K":
            return "K" in target_grade
        if "-" in target_grade:
            start, end = target_grade.split("-")
            if grade.isdigit() and start.isdigit() and end.isdigit():
                return int(start) <= int(grade) <= int(end)
            # Handle cases like "K-2"
            if start == "K" and grade == "K":
                return True
            if start == "K" and grade.isdigit():
                return int(grade) <= int(end)
        return grade == target_grade

    # Process each student to create a complete weekly schedule
    for _, student in df_students.iterrows():
        student_id = student['student_id']
        school_id = student['school_id']
        grade_level = student['grade_level']
        homeroom_id = student['homeroom_id']  # Track homeroom_id

        # Determine school type and core subjects
        if school_id <= 4:  # Elementary
            school_type = "Elementary"
            core_subjects = ELEMENTARY_CORE
            max_periods = 6  # Elementary schools have 6 periods
        elif school_id <= 7:  # Middle
            school_type = "Middle"
            core_subjects = MIDDLE_CORE
            max_periods = 6  # Middle schools have 6 periods
        elif school_id <= 9:  # High
            school_type = "High"
            core_subjects = HIGH_CORE
            max_periods = 6  # High schools have 6 periods
        else:  # Special Ed
            school_type = "SpecialEd"
            core_subjects = SPECIAL_CORE
            max_periods = 6  # Special Ed schools have 6 periods

        # Filter courses for this student's school and grade
        eligible_courses = []
        for _, course in df_courses[df_courses['school_id'] == school_id].iterrows():
            if is_grade_in_range(grade_level, course['target_grade_level']):
                eligible_courses.append(course.to_dict())

        if not eligible_courses:
            continue  # No eligible courses for this student

        # Get period data for this school - Uses the global generate_course_schedule function
        period_data = generate_course_schedule()

        # Initialize student schedule: {day: {period: course}}
        student_schedule = {day: {} for day in weekdays}

        # Track assigned course codes for specific handling
        assigned_course_codes = set()

        # Step 1: First assign core courses with fixed periods across multiple days
        for core_subject in core_subjects:
            # Find courses for this core subject
            core_options = [c for c in eligible_courses if c['subject_code'] == core_subject]

            if not core_options:
                continue  # No courses for this core subject

            # Pick a random core course
            selected_core = random.choice(core_options)
            assigned_course_codes.add(selected_core['course_code'])

            # Core subjects appear on 3-5 days per week
            days_per_week = random.randint(3, 5)
            course_days = random.sample(weekdays, days_per_week)

            # Find an available period that works across all selected days
            available_periods = list(range(1, max_periods + 1))
            random.shuffle(available_periods)  # Randomize period order

            for period in available_periods:
                # Check if this period works for all selected days
                valid_for_all_days = True
                for day in course_days:
                    if period in student_schedule[day]:
                        valid_for_all_days = False
                        break

                if valid_for_all_days:
                    # Assign this course to this period on all selected days
                    for day in course_days:
                        # Get period time data
                        period_time = period_data[period - 1]

                        student_schedule[day][period] = {
                            'course': selected_core,
                            'start_time': period_time['start_time'],
                            'end_time': period_time['end_time']
                        }
                    break

        # Step 2: Create a pool of electives for each student
        elective_options = [c for c in eligible_courses
                            if c['subject_code'] not in core_subjects
                            and c['course_code'] not in assigned_course_codes]

        # If we don't have enough electives, allow repeating core subjects
        if len(elective_options) < 20:  # Ensure we have enough variety
            additional_options = [c for c in eligible_courses
                                  if c['course_code'] not in assigned_course_codes]
            elective_options.extend(additional_options)

        # Step 3: Fill each day to exactly 6 classes (total 6 courses per student)
        for day in weekdays:
            # How many classes already assigned for this day?
            current_classes = len(student_schedule[day])

            # How many more classes needed to reach exactly 6?
            needed_classes = 6 - current_classes

            if needed_classes <= 0:
                continue  # Already have at least 6 classes

            # Find periods that need to be filled
            assigned_periods = set(student_schedule[day].keys())
            available_periods = sorted(list(set(range(1, max_periods + 1)) - assigned_periods))

            # Subjects already assigned today
            assigned_subjects_today = set([student_schedule[day][p]['course']['subject_code']
                                           for p in student_schedule[day]])

            # Fill exactly needed_classes periods
            for _ in range(needed_classes):
                if not available_periods:
                    break  # Shouldn't happen if max_periods >= 6

                period = available_periods.pop(0)

                # Prioritize courses with different subjects than already assigned today
                preferred_options = [e for e in elective_options
                                     if e['subject_code'] not in assigned_subjects_today]

                if not preferred_options:
                    preferred_options = elective_options  # Fallback to any available elective

                if not preferred_options:
                    # Final fallback: use any eligible course (could repeat)
                    preferred_options = eligible_courses

                # Select a course
                if preferred_options:
                    selected_course = random.choice(preferred_options)

                    # Get period time data
                    period_time = period_data[period - 1]

                    # Assign to schedule
                    student_schedule[day][period] = {
                        'course': selected_course,
                        'start_time': period_time['start_time'],
                        'end_time': period_time['end_time']
                    }

                    # Update tracking
                    assigned_subjects_today.add(selected_course['subject_code'])

                    # Remove from options if not a fallback
                    if selected_course in elective_options:
                        elective_options.remove(selected_course)

        # Step 4: Create final enrollment records
        for day in weekdays:
            # Verify we have exactly 6 classes scheduled
            if len(student_schedule[day]) != 6:
                # If we still don't have exactly 6, add or remove as needed
                assigned_periods = sorted(list(student_schedule[day].keys()))

                if len(assigned_periods) < 6:
                    # Need to add more periods
                    available_periods = sorted(list(set(range(1, max_periods + 1)) -
                                                    set(assigned_periods)))

                    while len(student_schedule[day]) < 6 and available_periods:
                        period = available_periods.pop(0)

                        # Pick any course
                        selected_course = random.choice(eligible_courses)
                        period_time = period_data[period - 1]

                        student_schedule[day][period] = {
                            'course': selected_course,
                            'start_time': period_time['start_time'],
                            'end_time': period_time['end_time']
                        }

                elif len(assigned_periods) > 6:
                    # Need to remove periods to get exactly 6
                    periods_to_remove = len(assigned_periods) - 6
                    for _ in range(periods_to_remove):
                        period_to_remove = max(assigned_periods)
                        del student_schedule[day][period_to_remove]
                        assigned_periods.remove(period_to_remove)

            # Create entries for this day
            for period in student_schedule[day]:
                course_data = student_schedule[day][period]
                course = course_data['course']

                # Create enrollment record for students in the same homeroom
                takes.append({
                    'enrollment_id': enrollment_id,
                    'student_id': student_id,
                    'subject_code': course['subject_code'],
                    'course_code': course['course_code'],
                    'semester': course['semester'],
                    'school_id': school_id,
                    'is_core': course['subject_code'] in core_subjects,
                    'weekday': day,
                    'period': period,
                    'start_time': course_data['start_time'],
                    'end_time': course_data['end_time'],
                    'homeroom_id': homeroom_id  # Ensure students in the same homeroom have same courses
                })
                enrollment_id += 1

    return pd.DataFrame(takes)


##### Generate Attendance Data #####
def generate_attendance_data(df_students, start_date='2025-01-15', end_date='2025-05-15'):
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
        '2025-01-20',  # MLK Day
        '2025-02-17',  # Presidents Day
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
    # Initialize empty list to store grade details
    grade_details = []
    grade_id = 1
    
    # Define grade type configurations
    grade_types = {
        'homework': {
            'count_range': (6,6),    
            'weight_range': (0.02, 0.05), 
            'score_mean': 85,      
            'score_std': 12          
        },
        'quiz': {
            'count_range': (3,3),  
            'weight_range': (0.05, 0.08),  
            'score_mean': 82,       
            'score_std': 15           
        },
        'mid exam': {
            'count_range': (1, 1),     
            'weight_range': (0.15, 0.25),  
            'score_mean': 78,          
            'score_std': 17      
        },
        'final exam': {
            'count_range': (1, 1),     
            'weight_range': (0.25, 0.35), 
            'score_mean': 76,       
            'score_std': 18          
        }
    }
    
    # Subject-specific score adjustments (modifiers to the base scores)
    subject_modifiers = {
        'MATH': {'mean_modifier': -5, 'std_modifier': 2},     # Math courses tend to have lower scores and higher variance
        'SCI': {'mean_modifier': -3, 'std_modifier': 2},      # Science courses similar to math
        'ENG': {'mean_modifier': 2, 'std_modifier': -1},      # English courses tend to have higher scores and lower variance
        'ELA': {'mean_modifier': 2, 'std_modifier': -1},      # Elementary Language Arts similar to English
        'HIST': {'mean_modifier': 3, 'std_modifier': -1},     # History courses tend to have higher scores
        'ART': {'mean_modifier': 8, 'std_modifier': -3},      # Art courses tend to have much higher scores and lower variance
        'PE': {'mean_modifier': 10, 'std_modifier': -5},      # PE courses tend to have the highest scores and lowest variance
    }
    
    # Filter df_takes to only include school_id values 5, 6, 7, 8, 9
    valid_school_ids = [5, 6, 7, 8, 9]
    df_takes_filtered = df_takes[df_takes['school_id'].isin(valid_school_ids)].copy()
    
    # Create a mapping of enrollment_id to student_id, subject_code, and course_code
    enrollment_info = df_takes_filtered[['enrollment_id', 'student_id', 'subject_code', 'course_code','school_id']].drop_duplicates()
    enrollment_map = {}
    for _, row in enrollment_info.iterrows():
        enrollment_map[row['enrollment_id']] = {
            'student_id': row['student_id'],
            'subject_code': row['subject_code'],
            'course_code': row['course_code'],
            'school_id': row['school_id']
        }
    
    # Group by the actual logical keys for enrollment
    enrollment_groups = df_takes_filtered.groupby(['student_id', 'course_code', 'subject_code'])
    
    # Process each unique student-course combination
    for (student_id, course_code, subject_code), group in enrollment_groups:
        # Get a representative enrollment_id for this student-course pair
        # Since a student can be enrolled in the same course on multiple days/periods
        enrollment_id = group['enrollment_id'].iloc[0]
        
        # Get subject-specific modifiers (if any)
        modifier = subject_modifiers.get(subject_code, {'mean_modifier': 0, 'std_modifier': 0})
        
        # Dictionary to track grade type counters for this enrollment
        type_counters = {'homework': 0, 'quiz': 0}
        
        # Generate all grade types for this enrollment
        total_weight = 0
        
        for grade_type, config in grade_types.items():
            # Determine how many grades of this type to generate
            count = random.randint(*config['count_range'])
            
            if grade_type == 'final exam' or grade_type == 'mid exam':
                # For exams, which have count=1
                # Make sure the total weight will sum close to 1.0 for final exam
                if grade_type == 'final exam':
                    remaining_weight = 1.0 - total_weight
                    # Ensure weight is in a reasonable range
                    weight = max(min(remaining_weight, config['weight_range'][1]), config['weight_range'][0])
                else:
                    # For mid exam, generate within range
                    weight = round(random.uniform(*config['weight_range']), 2)
                
                # Calculate score
                adjusted_mean = config['score_mean'] + modifier['mean_modifier']
                adjusted_std = max(3, config['score_std'] + modifier['std_modifier'])
                
                # Generate the score, bounded between 0-100
                raw_score = np.random.normal(adjusted_mean, adjusted_std)
                score = int(round(max(0, min(100, raw_score))))

                
                # Add to grade details
                grade_details.append({
                    'grade_id': grade_id,
                    'enrollment_id': enrollment_id,
                    'student_id': student_id,
                    'subject_code': subject_code,
                    'course_code': course_code,
                    'school_id': enrollment_map[enrollment_id]['school_id'],
                    'grade_type': grade_type,
                    'score': score,
                    'weight': weight
                })
                grade_id += 1
                total_weight += weight
            else:
                # Generate multiple homework and quiz grades
                # Dictionary to track grade type counters
                type_counter = {}
                if grade_type not in type_counter:
                    type_counter[grade_type] = 0
                
                for i in range(count):
                    # Increment the counter for this grade type
                    type_counter[grade_type] = i + 1
                    
                    # Create a numbered grade type (e.g., "homework1", "quiz2")
                    numbered_grade_type = f"{grade_type}{type_counter[grade_type]}"
                    
                    # Generate a weight within the configured range
                    weight = round(random.uniform(*config['weight_range']), 2)
                    
                    # Calculate score
                    adjusted_mean = config['score_mean'] + modifier['mean_modifier']
                    adjusted_std = max(3, config['score_std'] + modifier['std_modifier'])  # Ensure std dev isn't too small
                    
                    # Generate the score using a normal distribution, bounded between 0-100
                    raw_score = np.random.normal(adjusted_mean, adjusted_std)
                    score = int(round(max(0, min(100, raw_score))))
                    
                    # Add to grade details with additional info
                    grade_details.append({
                        'grade_id': grade_id,
                        'enrollment_id': enrollment_id,
                        'student_id': student_id,
                        'subject_code': subject_code,
                        'course_code': course_code,
                        'school_id': enrollment_map[enrollment_id]['school_id'],
                        'grade_type': numbered_grade_type,  # Use the numbered grade type
                        'score': score,
                        'weight': weight
                    })
                    grade_id += 1
                    total_weight += weight
    
    # Create DataFrame from the list
    df_grade_details = pd.DataFrame(grade_details)
    
    # Normalize weights to ensure they sum to 1.0 for each enrollment
    # Group by enrollment_id
    for enrollment_id in tqdm(df_grade_details['enrollment_id'].unique()):
        mask = df_grade_details['enrollment_id'] == enrollment_id
        enrollment_grades = df_grade_details[mask]
        
        # Calculate sum of weights
        weight_sum = enrollment_grades['weight'].sum()
        
        # Normalize weights
        if weight_sum > 0:  # Avoid division by zero
            df_grade_details.loc[mask, 'weight'] = df_grade_details.loc[mask, 'weight'] / weight_sum
            
            # Round to 2 decimal places
            df_grade_details.loc[mask, 'weight'] = df_grade_details.loc[mask, 'weight'].round(2)
            
            # Make sure the weights sum to exactly 1.0 by adjusting the final exam weight
            final_exam_mask = (df_grade_details['enrollment_id'] == enrollment_id) & (df_grade_details['grade_type'] == 'final exam')
            if any(final_exam_mask):
                adjusted_sum = df_grade_details.loc[mask & ~final_exam_mask, 'weight'].sum()
                df_grade_details.loc[final_exam_mask, 'weight'] = round(1.0 - adjusted_sum, 2)
    
    return df_grade_details

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
    df_students = generate_students(df_users, all_names, df_teachers)
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
    df_takes = generate_takes_data(df_students, df_courses)
    df_takes.to_csv("takes_data.csv", index=False)

    # Generate teaches data
    print("\nGenerating teaches data...")
    df_teaches = generate_teaches_data(df_courses, df_teachers, df_students)
    df_teaches.to_csv("teaches_data.csv", index=False)

    # # Generate attendance data
    # print("\nGenerating attendance data...")
    # df_attendance = generate_attendance_data(df_students)
    # df_attendance.to_csv("attendance_data.csv", index=False)

    # # Generate grade details
    # print("\nGenerating grade details...")
    # df_grade_details = generate_grade_details(df_takes)
    # df_grade_details.to_csv("grade_details.csv", index=False)

if __name__ == "__main__":
    main()