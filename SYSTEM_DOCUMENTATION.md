# LMS — System Documentation

A Django REST Framework backend for a school Learning Management System covering student enrolment, course delivery, assignments, quizzes, and grading.

---

## Table of Contents

1. [Tech Stack](#1-tech-stack)
2. [Project Structure](#2-project-structure)
3. [Architecture Overview](#3-architecture-overview)
4. [Data Model](#4-data-model)
5. [Authentication & Authorisation](#5-authentication--authorisation)
6. [Caching Strategy](#6-caching-strategy)
7. [File Storage](#7-file-storage)
8. [Business Logic](#8-business-logic)
9. [Signals & Automation](#9-signals--automation)
10. [Performance Design](#10-performance-design)
11. [Environment Variables](#11-environment-variables)
12. [Running Locally](#12-running-locally)
13. [Running Tests](#13-running-tests)
14. [CI/CD](#14-cicd)
15. [Deployment Checklist](#15-deployment-checklist)

---

## 1. Tech Stack

| Layer          | Technology                                       |
| -------------- | ------------------------------------------------ |
| Language       | Python 3.12                                      |
| Framework      | Django 4.2 + Django REST Framework               |
| Database       | PostgreSQL (via `psycopg2`)                      |
| Cache          | Redis via `django-redis`                         |
| Auth           | JWT via `djangorestframework-simplejwt`          |
| File storage   | AWS S3 via `django-storages` + `boto3`           |
| CORS           | `django-cors-headers`                            |
| Testing        | `pytest` + `pytest-django`                       |
| CI             | GitHub Actions                                   |

---

## 2. Project Structure

```
lms/
├── manage.py
├── requirements.txt
├── pytest.ini
├── .env                          # Local secrets (never commit)
├── API_DOCUMENTATION.md
├── SYSTEM_DOCUMENTATION.md
│
├── lms/                          # Django project config package
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
└── core/                         # Single Django app — all domain logic
    ├── models.py                 # All ORM models
    ├── views.py                  # All ViewSets
    ├── serializers.py            # All serializers
    ├── urls.py                   # DRF router registration
    ├── permissions.py            # Custom DRF permission classes
    ├── signals.py                # post_save signals (ID generation, auto-enroll)
    ├── cache.py                  # CACHE_TTL, CacheKeys, invalidation helpers
    ├── utils.py                  # S3 presigned URL generator
    ├── admin.py                  # Django admin registrations
    ├── apps.py                   # CoreConfig.ready() → connect signals
    ├── accounts/
    │   └── backends.py           # SchoolIDBackend (authenticate by school_id)
    ├── migrations/               # 20 database migrations
    └── tests/
        └── test_models.py        # Model signal tests
```

The entire domain lives in one app (`core`). This is intentional — the system is small enough that splitting into micro-apps would add indirection without benefit. If it grows significantly, natural split points would be: `accounts`, `academics`, `assessments`.

---

## 3. Architecture Overview

```
Client (web / mobile)
        │
        │  HTTPS + JWT
        ▼
┌───────────────────┐
│   Django / DRF    │   ← ViewSets, Serializers, Permissions
│   (WSGI / ASGI)   │
└────────┬──────────┘
         │                 ┌──────────────────┐
         ├────────────────▶│   PostgreSQL DB   │
         │                 └──────────────────┘
         │
         │                 ┌──────────────────┐
         ├────────────────▶│   Redis Cache     │
         │                 └──────────────────┘
         │
         │                 ┌──────────────────┐
         └────────────────▶│   AWS S3          │  (file uploads)
                           └──────────────────┘
```

All requests are handled synchronously. There is no task queue — every operation completes within the HTTP request/response cycle.

---

## 4. Data Model

### Entity Relationship Summary

```
User ──1:1──▶ Student ──M:M──▶ CourseOffering (through Enrollment)
User ──1:1──▶ Teacher ──M:M──▶ CourseOffering (assigned_course)
User ──1:1──▶ Admin
User ──1:1──▶ Principal

Programme ──1:M──▶ Section
Programme ──M:M──▶ Course (elective_courses)

Course ──1:M──▶ CourseOffering
CourseOffering ──1:M──▶ CourseOutline
CourseOffering ──1:M──▶ CourseResource
CourseOffering ──1:M──▶ Assignment ──1:M──▶ Submission
CourseOffering ──1:M──▶ Quiz ──1:M──▶ Question ──1:M──▶ Choice
                                               ──1:M──▶ ShortAnswerKey
              ──1:M──▶ QuizAttempt ──1:M──▶ StudentAnswer

CourseOffering ──1:M──▶ CourseOfferingTeacher ──1:M──▶ TimeSlot
Enrollment ──M:1──▶ CourseOfferingTeacher  (teaching_slot)
CourseOffering ──1:1──▶ GradeWeight

AcademicTerm  (school-wide singleton: is_current)
```

### Key Models

#### `User` (extends `AbstractUser`)
Custom user model. Extra fields: `email` (unique), `school_id` (unique, auto-set from profile signal). The `role` property derives the role from the presence of the related `student`, `teacher`, `admin`, or `principal` object.

#### `Student`
Profile record linked 1:1 to `User`. Fields: `student_number` (e.g. `STD001`), `programme`, `section`, `level` (1–3), `gender`, `current_gpa`, `cumulative_gpa`, `guardian_name/contact`. Auto-enrolls in core courses on creation via a signal.

#### `Teacher` / `Admin` / `Principal` (extend abstract `StaffBase`)
All share `employee_number`, `hire_date`, `date_of_birth`, `contact_number`. `Teacher` additionally has `department` and a M:M to `CourseOffering`. `Admin` and `Principal` set `user.is_staff = True` on creation.

#### `Programme`
A study programme (e.g. Science, Business). Has `max_electives_per_term` to cap student elective selections.

#### `Course`
A base course definition (`name`, `code_prefix`, `course_type` CORE/ELECTIVE, `credits`). Elective courses link to their eligible programmes via M:M.

#### `CourseOffering`
A specific offering of a course at a level and term (e.g. MTH Level 1 Term 1 → code `MTH101`). `unique_together = [course, level, term]`. Contains a `progress` property (% of outline entries marked COMPLETED).

#### `CourseOfferingTeacher`
Links a teacher to a course offering for a specific section (core) or as the sole instructor (elective, `section=None`). `unique_together = [course_offering, section]`. Has a `room` field.

#### `TimeSlot`
A day/time slot belonging to a `CourseOfferingTeacher`. Multiple slots per teacher slot represent multi-day meetings.

#### `Enrollment`
The M:M through model between `Student` and `CourseOffering`. Fields: `is_core`, `grade`, `teaching_slot` (FK to `CourseOfferingTeacher`, auto-assigned). `unique_together = [student, course_offering]`.

#### `AcademicTerm`
School-wide singleton for the current term. `save()` atomically unsets all other `is_current=True` terms. Controls `elective_selection_open` for student self-service enrolment.

#### `Assignment`
Created by a teacher for a course offering. Status: `draft → published → closed`. `due_date` and `max_attempts` enforce submission rules. `submission_count` and `graded_submission_count` are computed via DB annotation on list views.

#### `Submission`
A student's response to an assignment. `save()` enforces: at least one of `text_answer` or `file`, attempt limit, past-due check. Auto-sets `graded_at` on first grade, sets `graded_by` from the assignment's teacher.

#### `Quiz`
Teacher-created quiz with `start_time`/`end_time` window, `duration_minutes`, `max_attempts`. Status: `draft → published → closed`. `total_marks` is the sum of all question marks, computed via DB annotation on list views.

#### `Question`
Belongs to a quiz. Types: `mcq_single`, `mcq_multiple`, `true_false`, `short_answer`. Can only be created/modified while quiz is `draft`.

#### `Choice`
A possible answer for MCQ / true-false questions. Validates: MCQ single — exactly one correct; true/false — max 2 choices with values `"True"` / `"False"`; short answer — no choices allowed.

#### `ShortAnswerKey`
Accepted answer string for short-answer questions. Normalised to lowercase on save.

#### `QuizAttempt`
A student's attempt at a quiz. Tracks `status` (in_progress / submitted / graded), `marks_obtained`, timing. `auto_grade_all()` grades MCQ/true-false answers automatically; short-answer marks must be applied manually by the teacher.

#### `StudentAnswer`
A student's response to a single question within an attempt. `auto_grade()` implements: MCQ single (full marks or 0), MCQ multiple (partial marks proportional to correct choices), true/false (full or 0), short answer (exact key match).

#### `GradeWeight`
1:1 with `CourseOffering`. Controls the assignment weight and quiz weight used in the gradebook calculation. Defaults to 50/50 when absent.

---

## 5. Authentication & Authorisation

### Authentication

The system uses two authentication methods:

**1. Custom login (`POST /api/users/login/`)**
- Accepts `role`, `school_id`, `password`
- Uses `SchoolIDBackend` (`core/accounts/backends.py`) which looks up users by `school_id`
- Validates the role matches the user's actual role
- Returns a SimpleJWT access token (4 h) and refresh token (7 d)
- Response is cached per `role:school_id` pair to avoid re-serialising on rapid re-logins

**2. StandardJWT endpoints** (`/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/token/blacklist/`)
- SimpleJWT standard endpoints for token obtain, refresh, and blacklist
- Refresh tokens rotate on use and old tokens are blacklisted

All other endpoints require `Authorization: Bearer <access_token>`.

### Authorisation

DRF permission classes control access. The **global default** is `IsAuthenticated` — every endpoint requires a valid token unless it explicitly overrides to `AllowAny`.

**Custom permission classes** (`core/permissions.py`):

| Class              | Grants access when…                                             |
| ------------------ | --------------------------------------------------------------- |
| `IsStudent`        | `hasattr(request.user, 'student')`                              |
| `IsTeacher`        | `hasattr(request.user, 'teacher')`                              |
| `IsAdmin`          | `user.is_staff or user.is_superuser`                            |
| `IsTeacherOrAdmin` | Either of the above two                                         |
| `IsOwnerOrAdmin`   | Object-level: admin always; else checks `obj.user/student/teacher` |
| `IsEnrolledStudent`| Object-level: student has an active enrollment in same term    |
| `IsTeacherOfCourse`| Object-level: `obj.teacher == request.user.teacher`            |

**Role-based queryset scoping** is performed inside each `get_queryset()` method to ensure users never see data outside their scope, regardless of the ID they pass.

---

## 6. Caching Strategy

### Backend

Redis via `django-redis`. Configured by the `REDIS_URL` environment variable (defaults to `redis://127.0.0.1:6379/1`). All processes share the same cache, making it safe for multi-worker deployments.

### Key Design

All cache keys are defined in `core/cache.py` via the `CacheKeys` class. Every key is prefixed with `lms:` for namespace isolation:

```
lms:login:{role}:{school_id}
lms:user_me:{user_id}
lms:current_term
lms:student:{id}:enrollments
lms:offering:{id}:assignments
lms:quiz:{id}:detail
lms:offering:{offering_id}:student:{student_id}:gradebook
...
```

### TTL Constants

All durations live in `CACHE_TTL` in `cache.py`. Tune there without touching viewset code.

### Invalidation

Every write operation (create / update / delete) calls one of the `invalidate_*` helpers in `cache.py`, which deletes the precise set of keys that become stale. No broad cache flushes. Invalidation is synchronous — the cache is cleared before the HTTP response is returned.

Hierarchy:
- Mutating a `Submission` clears: student cache, offering cache, per-student gradebook
- Mutating an `Assignment` clears: offering cache, teacher cache, all enrolled students' assignment caches
- Mutating an `Enrollment` clears: student cache, offering cache, all teachers' student-list caches

### Bulk Flush

To wipe all LMS keys (e.g. after a data migration):

```python
from django_redis import get_redis_connection
get_redis_connection("default").delete_pattern("lms:*")
```

---

## 7. File Storage

All user-uploaded files (assignment attachments, submissions, course resources) are stored in **AWS S3** via `django-storages` (`S3Boto3Storage`).

Static files remain local (served by the web server or a CDN separately).

### Upload paths

| Model           | S3 key pattern                                                        |
| --------------- | --------------------------------------------------------------------- |
| `Assignment`    | `assignments/{course_code}/{assignment_id}/{filename}`                |
| `Submission`    | `submissions/{course_code}/{assignment_id}/{student_number}/{filename}`|
| `CourseResource`| `course_resources/{course_code}/{term}/{type}/{filename}`             |

### Serving files

Files are served via **S3 presigned URLs** (`AWS_QUERYSTRING_AUTH = True`, `AWS_S3_SIGNATURE_VERSION = s3v4`). Signed URLs expire after 1 hour by default. The `generate_presigned_url(key)` utility in `core/utils.py` generates them on demand.

Object-level cache control is set to `max-age=86400` (1 day) for browser caching of static resources.

---

## 8. Business Logic

### Role Derivation

A user's role is not stored as a field. It is derived at runtime from the presence of related objects:

```python
@property
def role(self):
    if hasattr(self, 'student'):   return 'student'
    if hasattr(self, 'teacher'):   return 'teacher'
    if self.is_superuser:          return 'superadmin'
    if self.is_staff:              return 'admin'
    return 'user'
```

### Course Codes

Course codes are computed: `{course.code_prefix}{level}0{term}`. Example: Mathematics (`MTH`), Level 1, Term 1 → `MTH101`.

### Course Progress

`CourseOffering.progress` returns the percentage of `CourseOutline` entries with `status = "completed"`. When the outline queryset is prefetched, the calculation is done in Python (zero extra queries). Otherwise it performs one DB query.

### Gradebook

Computed in `CourseOfferingViewSet.gradebook()` using configurable weights from `GradeWeight`:

```
weighted_score = (
    (assignment_score * assignments_weight) +
    (quiz_score       * quizzes_weight)
) / active_weight
```

Only categories with at least one graded entry contribute to `active_weight`, so a student who has only graded assignments but no quiz attempts gets a meaningful partial score rather than an artificially diluted one.

Letter grade scale: A (≥80), B+ (≥75), B (≥70), C+ (≥65), C (≥60), D+ (≥55), D (≥50), E (≥45), F (<45).

The result is cached per student per offering for 5 minutes and invalidated when a submission is graded.

### Quiz Auto-Grading

`StudentAnswer.auto_grade()` implements:

- **MCQ single**: full marks if the selected choice is correct, else 0.
- **MCQ multiple**: partial marks = `(correct_selections - wrong_selections) / total_correct_choices * question.marks`, floored at 0.
- **True / False**: full marks or 0.
- **Short answer**: checks `text_answer.strip().lower()` against all `ShortAnswerKey` records; full marks if matched, else 0. Unmatched short answers remain `marks_awarded = null` for manual review.

### Elective Selection

Enforced in `EnrollmentViewSet.select_electives()`:

1. `AcademicTerm.elective_selection_open` must be `True`
2. Each offering's `level` must match the student's `level`
3. The course must be listed as an elective for the student's programme
4. The student must not already be enrolled in the offering
5. The total selected electives must not exceed `programme.max_electives_per_term`

### Teaching Slot Assignment

When an enrollment is created, `_assign_teaching_slot()` automatically finds the correct `CourseOfferingTeacher` record:

- **Core courses**: matches on `course_offering + student.section`
- **Elective courses**: the sole slot where `section = None`

This populates `Enrollment.teaching_slot`, which the `EnrollmentSerializer` uses to expose `teacher`, `room`, and `schedule` fields.

### Attempt Limits

Both `Submission` and `QuizAttempt` enforce `max_attempts`. `Submission.clean()` raises a `ValidationError` before saving if the limit is reached or the due date has passed.

---

## 9. Signals & Automation

All signals are `post_save` and registered in `CoreConfig.ready()`.

| Signal                          | Trigger               | Action                                                                 |
| ------------------------------- | --------------------- | ---------------------------------------------------------------------- |
| `generate_student_number`       | Student created       | Sets `student_number = STD{id:03d}`, copies to `user.school_id`       |
| `generate_employee_number_teacher` | Teacher created    | Sets `employee_number = TCH{id:03d}`, copies to `user.school_id`      |
| `generate_employee_number_admin`   | Admin created      | Sets `employee_number = ADM{id:03d}`, copies to `user.school_id`      |
| `generate_employee_number_principal` | Principal created | Sets `employee_number = PRN{id:03d}`, copies to `user.school_id`    |
| `enroll_in_core_courses`        | Student created       | Auto-enrolls in all active `CORE` offerings matching the student's level and current term number |

The auto-enroll signal calls `get_current_term()` and `Enrollment.objects.create()` in a loop. If no current term is set, the signal exits silently.

---

## 10. Performance Design

### Database Queries

Every ViewSet `get_queryset()` uses `select_related` and `prefetch_related` to eliminate N+1 queries:

| ViewSet            | Optimisations                                                          |
| ------------------ | ---------------------------------------------------------------------- |
| `StudentViewSet`   | `select_related("user", "programme")`                                  |
| `TeacherViewSet`   | `select_related("user")`, `prefetch_related("assigned_course")`        |
| `CourseOfferingViewSet` | `select_related("course")`, `prefetch_related("outline")`         |
| `EnrollmentViewSet`| `select_related("student__user", "course_offering__course", "teaching_slot__teacher__user", "teaching_slot__section")`, `prefetch_related("teaching_slot__time_slots")` |
| `AssignmentViewSet`| `select_related("course_offering__course", "teacher__user")`, `annotate(_ann_submission_count, _ann_graded_submission_count)` |
| `QuizViewSet`      | `select_related("course_offering__course", "teacher__user")`, `prefetch_related("questions__choices", "questions__answer_keys")`, `annotate(_ann_total_marks)` |

### Annotation-Backed Serializer Fields

`AssignmentSerializer.submission_count` and `graded_submission_count`, and `QuizSerializer.total_marks`, use `SerializerMethodField` that reads DB-level annotations when present (set by list-view querysets) and falls back to model properties for single-object access. This eliminates 2–3 extra queries per row in list views.

### Gradebook

The gradebook endpoint previously performed `N + 2M` queries (N assignments, M quizzes). It now uses:

- `Prefetch("submissions", queryset=..., to_attr="student_submissions")` — all student submissions in 1 query
- `Prefetch("attempts", queryset=..., to_attr="student_attempts")` — all student attempts in 1 query
- `annotate(_gb_total_marks=Sum("questions__marks"))` — quiz total marks without extra round-trips

Total queries regardless of course size: 4 (weights, assignments+submissions, quizzes+attempts, offering).

### Quiz List

The quiz list action previously ran 1 query per quiz to count a student's attempts. This is now a single aggregated query:

```python
QuizAttempt.objects.filter(quiz_id__in=quiz_ids, student=student)
    .values('quiz_id')
    .annotate(cnt=Count('id'))
```

### Cache Invalidation Cost

Cache invalidation helpers build key lists in Python and call `cache.delete_many()` once. The helpers that iterate enrolled students (`invalidate_assignment_caches`, `invalidate_quiz_caches`) now use a single `Enrollment.values_list("student_id")` query rather than the previous two-query pattern.

### Indexes

| Model           | Indexed fields                                |
| --------------- | --------------------------------------------- |
| `User`          | `email`, `school_id`                          |
| `Student`       | `student_number`                              |
| `Teacher / Admin / Principal` | `employee_number`               |
| `Course`        | `course_type`                                 |
| `CourseOffering`| `(level, term)`                               |
| `Enrollment`    | `(student, is_core)`, `course_offering`       |
| `Assignment`    | `(course_offering, status)`, `due_date`       |
| `Submission`    | `(assignment, is_graded)`, `(student, status)`|
| `Quiz`          | `(course_offering, status)`, `(start_time, end_time)` |

---

## 11. Environment Variables

Create a `.env` file in the project root. All variables are loaded via `python-dotenv`.

| Variable                 | Required | Description                                      |
| ------------------------ | -------- | ------------------------------------------------ |
| `SECRET_KEY`             | Yes      | Django secret key                                |
| `DEBUG`                  | No       | `true` for dev, omit or `false` for production   |
| `DATABASE_NAME`          | Yes      | PostgreSQL database name                         |
| `DATABASE_USER`          | Yes      | PostgreSQL username                              |
| `DATABASE_PASSWORD`      | Yes      | PostgreSQL password                              |
| `DATABASE_HOST`          | Yes      | PostgreSQL host (e.g. `localhost`)               |
| `DATABASE_PORT`          | Yes      | PostgreSQL port (e.g. `5432`)                    |
| `REDIS_URL`              | No       | Redis connection URL. Default: `redis://127.0.0.1:6379/1` |
| `AWS_ACCESS_KEY_ID`      | Yes      | AWS access key for S3                            |
| `AWS_SECRET_ACCESS_KEY`  | Yes      | AWS secret key for S3                            |
| `AWS_STORAGE_BUCKET_NAME`| Yes      | S3 bucket name                                   |
| `AWS_S3_REGION_NAME`     | Yes      | S3 bucket region (e.g. `eu-west-3`)              |
| `CORS_ALLOW_ALL_ORIGINS` | No       | `true` to allow all origins (dev only)           |
| `CORS_ALLOWED_ORIGINS`   | No       | Comma-separated list of allowed origins (production) |

---

## 12. Running Locally

### Prerequisites

- Python 3.12
- PostgreSQL (running)
- Redis (running)

### Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd lms

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate     # macOS / Linux
.venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env          # then fill in your values

# Apply migrations
python manage.py migrate

# Create a superuser (optional, for Django admin access)
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000/api/`.

The Django admin panel is at `http://127.0.0.1:8000/admin/`.

---

## 13. Running Tests

```bash
pytest -v
```

Tests use `pytest-django` with the `DJANGO_SETTINGS_MODULE` set in `pytest.ini`. The CI pipeline runs tests against a real PostgreSQL 16 instance — **no database mocking is used**.

Current test coverage: model signal tests (student and staff number generation).

### Adding Tests

Place new test files in `core/tests/`. Name them `test_*.py`. Mark database tests with `@pytest.mark.django_db`.

---

## 14. CI/CD

GitHub Actions workflow at `.github/workflows/ci.yml`. Runs on push and pull requests to `main`.

**Pipeline steps:**

1. Spin up a PostgreSQL 16 service container
2. Set up Python 3.12
3. Install dependencies (`pip install -r requirements.txt`)
4. Run `pytest -v` with test environment variables

All merges to `main` must pass CI.

---

## 15. Deployment Checklist

Before deploying to production:

- [ ] Set `DEBUG=false` in the environment
- [ ] Set a strong, unique `SECRET_KEY`
- [ ] Set `ALLOWED_HOSTS` to your domain(s) in `settings.py`
- [ ] Set `CORS_ALLOWED_ORIGINS` (comma-separated) instead of `CORS_ALLOW_ALL_ORIGINS=true`
- [ ] Ensure `REDIS_URL` points to a persistent, production Redis instance
- [ ] Ensure the PostgreSQL database is backed up and connections are pooled (e.g. PgBouncer)
- [ ] Ensure AWS S3 bucket has appropriate access policies; confirm `AWS_QUERYSTRING_AUTH=True`
- [ ] Run `python manage.py migrate` before starting the new version
- [ ] Run `python manage.py collectstatic` if serving static files from the app
- [ ] Configure a production WSGI/ASGI server (Gunicorn or Uvicorn) with multiple workers
- [ ] Set up HTTPS (TLS) — JWT tokens must never travel over plain HTTP
- [ ] Configure log rotation and error alerting (e.g. Sentry)
- [ ] Set `SIMPLE_JWT.SIGNING_KEY` to a dedicated secret key separate from `SECRET_KEY` if needed

### WSGI (Gunicorn) example

```bash
gunicorn lms.wsgi:application \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 30
```

Because the cache backend is Redis (shared across processes), all four workers share a consistent cache — unlike the previous `LocMemCache` which gave each worker its own isolated cache.
