# School District Management System

A database-driven application for managing academic data across multiple schools within a district. The platform integrates a **graphical user interface (GUI)** with both an **operational database** (for day-to-day tasks) and an **analytical database** (for reporting and insights).

---

## Overview
The system centralizes school operations and provides **role-based access** for students, guardians, teachers, and administrators. Each user has a tailored experience:

- **Teachers**: record attendance, enter grades, manage courses  
- **Students**: view grades, attendance, and enrollment  
- **Guardians**: monitor their child’s progress and communicate with teachers  
- **Administrators**: oversee district-wide performance and generate analytical reports  

---

## Features
- Add, view, and modify **student, teacher, guardian, and administrator** profiles  
- Enroll students in courses and assign teachers  
- Record **attendance** and update **grades**  
- Role-based access with **personalized dashboards**  
- District-level reporting on **performance and attendance trends**  

---

## Architecture
- **Operational Database**: Supports real-time updates as users interact with the system  
- **Analytical Database**: Star schema designed for dimensional modeling and reporting (e.g., attendance rates, grade distributions)  
- **GUI**: Intuitive interface for data entry, queries, and dashboards  

---

## Tech Stack
- **Backend/Database**: MySQL (migrated demo version available in SQLite for portability)  
- **Frontend**: PyQt (GUI)  
- **Data Engineering**: ETL workflows, star schema modeling, stored procedures  

---

## Demo
For ease of access, the repository includes:
- **Pre-seeded demo accounts** (so you don’t need to create new users)  
- **SQLite version of the database** with sample data for quick setup  
- **Screenshots and schema diagrams** for fast review without running the code  
