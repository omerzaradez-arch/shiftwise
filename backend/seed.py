"""
Seed script — creates demo restaurant with employees, templates, and org.
Run: python seed.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import time
from app.database import SyncSessionLocal, sync_engine
from app.database import Base
from app.models import Organization, Employee, ShiftTemplate
from app.security import hash_password
import uuid


def seed():
    Base.metadata.create_all(bind=sync_engine)

    with SyncSessionLocal() as db:
        # Check if already seeded
        if db.query(Organization).first():
            print("Already seeded. Skipping.")
            return

        # Create organization
        org = Organization(
            id=str(uuid.uuid4()),
            name="מסעדת השף",
            plan="pro",
            timezone="Asia/Jerusalem",
        )
        db.add(org)
        db.flush()

        # Create employees
        employees_data = [
            {"name": "יוסי כהן", "phone": "0501111111", "role": "manager", "employment_type": "full_time", "max_hours": 45},
            {"name": "שרה לוי", "phone": "0502222222", "role": "senior", "employment_type": "full_time", "max_hours": 40},
            {"name": "דוד מזרחי", "phone": "0503333333", "role": "senior", "employment_type": "full_time", "max_hours": 40},
            {"name": "ריבה אברהם", "phone": "0504444444", "role": "junior", "employment_type": "part_time", "max_hours": 25},
            {"name": "מיכל גורן", "phone": "0505555555", "role": "junior", "employment_type": "part_time", "max_hours": 20},
            {"name": "אורי שפירא", "phone": "0506666666", "role": "junior", "employment_type": "part_time", "max_hours": 20},
            {"name": "נועה ברק", "phone": "0507777777", "role": "trainee", "employment_type": "casual", "max_hours": 15},
            {"name": "אמיר דהן", "phone": "0508888888", "role": "junior", "employment_type": "part_time", "max_hours": 25},
        ]

        for emp_data in employees_data:
            db.add(Employee(
                id=str(uuid.uuid4()),
                org_id=org.id,
                name=emp_data["name"],
                phone=emp_data["phone"],
                hashed_password=hash_password("1234"),
                role=emp_data["role"],
                employment_type=emp_data["employment_type"],
                max_hours_per_week=emp_data["max_hours"],
                min_hours_per_week=0,
                max_consecutive_days=5,
                skills=[],
            ))

        # Create shift templates (all days Sun-Thu + Fri)
        all_week = [0, 1, 2, 3, 4, 5, 6]   # Sun=0 ... Sat=6
        weekdays = [0, 1, 2, 3, 4]
        all_days_no_sat = [0, 1, 2, 3, 4, 5]  # Sun-Fri

        templates = [
            {
                "name": "משמרת בוקר",
                "shift_type": "morning",
                "start_time": time(8, 0),
                "end_time": time(16, 0),
                "min_employees": 2,
                "max_employees": 4,
                "required_roles": {"senior": 1},
                "days_of_week": all_days_no_sat,
            },
            {
                "name": "משמרת ערב",
                "shift_type": "evening",
                "start_time": time(16, 0),
                "end_time": time(23, 30),
                "min_employees": 3,
                "max_employees": 5,
                "required_roles": {"senior": 1},
                "days_of_week": all_days_no_sat,
            },
            {
                "name": "משמרת צהריים (שישי)",
                "shift_type": "afternoon",
                "start_time": time(11, 0),
                "end_time": time(17, 0),
                "min_employees": 3,
                "max_employees": 6,
                "required_roles": {"senior": 1},
                "days_of_week": [5],  # Friday only
            },
        ]

        for t_data in templates:
            db.add(ShiftTemplate(
                id=str(uuid.uuid4()),
                org_id=org.id,
                **t_data,
            ))

        db.commit()
        print(f"Seeded org: {org.name} (id: {org.id})")
        print("Employees created with password: 1234")
        print("Shift templates: בוקר, ערב, שישי צהריים")


if __name__ == "__main__":
    seed()
