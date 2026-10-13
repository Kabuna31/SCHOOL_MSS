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
`migrate_schemas` during preparation or when schema tenancy is enabled. WSGI
startup does not run migrations.
