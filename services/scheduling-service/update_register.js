const fs = require('fs');
const file = 'c:/Users/asus/Downloads/SEP project Repo/Backend/services/scheduling-service/app/services/user_service.py';
let c = fs.readFileSync(file, 'utf8');

c = c.replace(/def register_student\(db: Session, data: StudentRegistrationRequest, current_user_id: UUID\):/g, 
`from shared_core.schemas.identity import StudentRegistrationRequest, LecturerRegistrationRequest, AdminRegistrationRequest
from typing import Union

def register_user(db: Session, data: Union[StudentRegistrationRequest, LecturerRegistrationRequest, AdminRegistrationRequest], current_user_id: UUID):`);

// In the supabase payload, replace `"role": "student"` with `"role": data.role`
c = c.replace(/"role": "student",/g, '"role": data.role,');

// In Postgres user_data, replace `"role": "student"` with `"role": data.role`
// We did that globally in the previous line! But wait, `data.role` is a string, which is good.

// The student profile creation logic:
c = c.replace(/    # 3\. Create Student in Postgres[\s\S]*?(?=    return user_repository\.get_user\(db, new_user_id\))/g, 
`    # 3. Create Profile in Postgres
    if data.role == "student":
        student_data = {
            "id": new_user_id,
            "student_index_no": getattr(data, "student_index_no", None),
            "full_name": getattr(data, "full_name", None),
            "name_with_initials": getattr(data, "name_with_initials", None),
            "display_name": getattr(data, "display_name", None),
            "department_id": getattr(data, "department_id", None),
            "academic_year_id": getattr(data, "academic_year_id", None),
            "date_of_birth": getattr(data, "date_of_birth", None),
            "gender": getattr(data, "gender", None),
            "nic": getattr(data, "nic", None),
            "contact_number": getattr(data, "contact_number", None),
            "address": getattr(data, "address", None),
            "registered_by": current_user_id
        }
        user_repository.create_student(db, student_data)
    elif data.role == "lecturer":
        lecturer_data = {
            "id": new_user_id,
            "lecturer_code": getattr(data, "employee_id", None),
            "display_name": getattr(data, "display_name", getattr(data, "full_name", None)),
            "department_id": getattr(data, "department_id", None),
            "email": data.email,
            "contact_number": getattr(data, "contact_number", None),
        }
        user_repository.create_lecturer(db, lecturer_data)
    
`);

fs.writeFileSync(file, c);
