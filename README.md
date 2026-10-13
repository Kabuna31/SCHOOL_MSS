# Django School Management System
This an open source school management system API built with Django and Django-rest framework for managing school or college. It provides an API for administration, admission, attendance, schedule and results. It also provide users with different permissions to access various apps depending on their access level.

Techdometz is a tech startup helping schools and education centers to provide solutions to their tech problems. 
[Contact us](http://techdometz.com/contact-us/) for details.

# Quick Install
You should have at least basic django and django-rest framework experience to run django-scms. We test only in PostgreSQL database.

### Fork the repo
You first need to fork the repo from [Techdometz](https://github.com/TechDometz/django-scms).
### Clone the repo
Clone the forked repo

`git clone https://github.com/[username]/django-scms.git`  

### Create a virtual environment

There are several ways depending on the OS and package you choose. Here's my favorite  
`sudo apt-get install python3-pip`  
`pip3 install virtualenv`  
Then either  
`python3 -m venv venv`  
or  
`python -m venv venv`  
or  
`virtualenv venv` (you can call it venv or anything you like)

#### Activate the virtual environment  

in Mac or Linux
`source venv/bin/activate`  
in windows
`venv/Scripts/activate.bat`  


## 🚀 Key Features

- 🔐 **Authentication & Role-Based Access Control**:  
  Supports authentication and permission control for:
  - **Admins**
  - **Teachers**
  - **Accountants**
  - **Parents**

- 💸 **Finance Module** *(NEW)*:  
  - Manage **Receipts**
  - Track **Payments**
  - Generate **Financial Reports**

- 🧾 **School Information System (SIS)**:
  - Tracks student records and their associated parent/guardian contacts.
  - Manages class and academic year data.
  - Required module for all other apps.

- 📝 **Admissions**:
  - Manages student admission pipeline and levels.
  - Tracks marketing channels and open house participation.

---

## 🔧 Upcoming Features

- 📅 **Schedule Management**
- 🧠 **Examinations and Grading**
- 📚 **Digital Notes and Materials**
- 📊 **Attendance Tracking**

---

## Contributors

- [Mwinamijr](https://github.com/mwinamijr)

## License

The project is licensed under the MIT License

## PostgreSQL schema tenancy

The optional django-tenants configuration routes school URL prefixes to
separate PostgreSQL schemas on the existing Render hostname, for example
`https://your-service.onrender.com/t/school-slug/api/`. It is disabled by
default so existing shared-table data is not redirected to empty tenant
schemas.

Before enabling it:

1. Back up the existing database and prepare a PostgreSQL database.
2. Test the new staged ownership migrations on a restored database backup
   before deploying. They derive school ownership from related records where
   possible and use a sole `School` record only when ownership is otherwise
   unknown. If a row is linked to conflicting schools, or has no related school
   while multiple schools exist, the migration stops and reports the row rather
   than guessing. Resolve those rows explicitly before retrying.
3. Set `DATABASE_URL` to the verified PostgreSQL database and
   `TENANCY_PREPARATION=1`. This configures PostgreSQL and schema-aware
   migrations without switching tenant request routing.
4. Run `python manage.py migrate_deployment`, then
   `python manage.py ensure_public_tenant`.
5. Provision each schema with
   `python manage.py create_school_tenant --school-id <id> --schema-name <slug> --slug <url-slug>`.
6. Transfer each school's existing records from the shared tables to its
   schema and verify record counts and tenant isolation. Tenant setup does not
   transfer existing business data automatically.
7. Only after verification, set `TENANCY_DATA_MIGRATION_COMPLETE=1` and
   `TENANCY_ENABLED=1`. School endpoints will then be served under
   `/t/<tenant-slug>/` on the Render hostname.

The `tenants.SchoolTenant` registry links a public school record to its schema.
Schema creation is deliberately disabled on model save. During preparation,
create the public tenant registry with `python manage.py ensure_public_tenant`,
then provision school schemas with `python manage.py create_school_tenant`.
Provisioning seeds school metadata and weekdays; it does not migrate existing
business records. Deployments run
`migrate_deployment`, which uses Django migrations in legacy mode and
`migrate_schemas` during preparation or when schema tenancy is enabled. On
Render, use `python manage.py migrate_deployment` as the release/pre-deploy
command and `gunicorn school.wsgi:application --bind 0.0.0.0:$PORT` as the
web start command; do not chain migrations into the web start command.

Authentication and user identities remain shared in the public schema.
Academic, attendance, examination, finance, notes, schedule, and SIS models are
created in tenant schemas. The administration app is present in both schemas:
the public `School` record is the tenant registry source, and provisioning
copies its school metadata and weekdays into the school schema. Keep tenant
routing disabled until a school schema is provisioned and tenant login,
permissions, and school-data isolation have been tested on PostgreSQL.

### School Excel bulk import and export

Tenant bulk-import endpoints are under `/t/<tenant-slug>/api/` and accept an
`.xlsx` workbook as multipart form field `file`. The first worksheet is used;
its first row is treated as a header, and each following row must put values in
the order below. Use the listed names as headers for clarity. Imports require
an authenticated user associated with that school; school events additionally
require an admin user.

| Data | Import endpoint suffix | Export endpoint suffix | Import column order |
| --- | --- | --- | --- |
| Users | `users/users/bulk-upload/` | `users/users/export/` | `email`, `first_name`, `middle_name`, `last_name` |
| Teachers | `users/teachers/bulk-upload/` | `users/teachers/export/` | `first_name`, `middle_name`, `last_name`, `phone_number`, `employment_id`, `short_name`, `subject_specialization`, `address`, `gender`, `date_of_birth`, `salary`, `email` |
| Subjects | `academic/subjects/bulk-upload/` | `academic/subjects/export/` | `name`, `subject_code`, `department` |
| Classrooms | `academic/classrooms/bulk-upload/` | `academic/classrooms/export/` | `name`, `stream`, `class_teacher` |
| Students | `sis/students/bulk-upload/` | `sis/students/export/` | `first_name`, `middle_name`, `last_name`, `admission_number`, `parent_contact`, `religion`, `class_level`, `gender` |
| Student-class enrollment | `academic/student-classes/bulk-upload/` | `academic/student-classes/export/` | `classroom_name`, `stream_name`, `academic_year`, `student_full_name`, `student_admission_number` |
| Marks | `examination/marks/bulk-upload/` | `examination/marks/export/` | `exam_name`, `student_admission_number`, `classroom_name`, `stream_name`, `academic_year`, `subject_code`, `points_scored`, `created_by_emp_id` |
| Receipts | `finance/receipts/bulk-upload/` | `finance/receipts/export/` | `payer`, `first_name`, `middle_name`, `last_name`, `paid_for`, `paid_through`, `payment_date`, `term`, `amount` |
| School events | `administration/school-events/bulk-upload/` | `administration/school-events/export/` | `name`, `event_type`, `term_id`, `start_date`, `end_date`, `description` |

Export endpoints return `.xlsx` attachments scoped to the authenticated user's
school. The Users export matches the user-management list (parents have their
own endpoint) and never includes passwords. User imports accept names and
email only: they assign the current school, grant no role, and create an
unusable password that an administrator must set up. Teacher imports use the
optional email in the last column when supplied; otherwise it is generated as
`first.last@hayatul.com`. Imported teacher accounts also have unusable
passwords until account setup or a password reset.

Create reference records before importing rows that depend on them: departments
and class levels, streams, academic years, terms, and receipt allocations must
already exist. Import subjects before teachers; classrooms need their class,
stream, and class teacher (identified by employment ID or full name); students
need their class level; enrollments need students and classrooms; marks need an
exam assigned to the class, a student enrollment, subject, academic year, and
teacher. A teacher uploading marks is recorded as the creator; administrators
must provide a same-school teacher's employment ID in `created_by_emp_id`.
Receipts need students, receipt allocations, and terms. School events need a
valid term ID. Teacher subject specializations are comma-separated subject
names. Dates should use Excel dates or `YYYY-MM-DD`; receipt terms use
`Term 1-2024` format, matching the term name and academic-year name in the
school. Student-class imports can match by `student_admission_number`; if it
is blank, they use `student_full_name`.

Rows are validated independently. Invalid rows are reported in the response
instead of preventing unrelated valid rows from being imported; check the
response's `not_created` or equivalent error list before treating an upload as
complete. Parent accounts created by student imports also require account
setup before login.

### Graded assignment submissions

Within the school API prefix, authenticated parent accounts can list their
children's graded assignments with `GET assignments/graded/` and submit an
attempt with `POST assignments/graded/submit/`. A submission uses the
assignment ID, the linked student's ID, and a map of question IDs to the
selected choice text:

```json
{
  "assignment_id": 12,
  "student_id": 34,
  "answers": {
    "101": "Four",
    "102": "Eight"
  }
}
```

Only children linked to the authenticated parent and assignments belonging
to the same school are accepted. Omitted questions count as incorrect, and
assignments without gradable questions are rejected.
