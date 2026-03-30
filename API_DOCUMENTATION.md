# LMS — API Documentation

**Base URL:** `/api/`

**Authentication:** JWT Bearer Token — include `Authorization: Bearer <access_token>` on every request except `POST /api/users/login/`.

**Content-Type:** `application/json`

---

## Role Abbreviations

| Symbol     | Role                      |
| ---------- | ------------------------- |
| 🔓         | Public (no auth required) |
| 👤         | Any authenticated user    |
| 🧑‍🎓     | Student only              |
| 👩‍🏫     | Teacher only              |
| 🏫         | Principal only            |
| 🛡️       | Admin only                |
| 🛡️👩‍🏫 | Teacher or Admin          |

---

## Table of Contents

1. [Users](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#1-users)
2. [Students](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#2-students)
3. [Teachers](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#3-teachers)
4. [Principals](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#4-principals)
5. [Programmes](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#5-programmes)
6. [Courses](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#6-courses)
7. [Course Offerings](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#7-course-offerings)
8. [Enrollments](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#8-enrollments)
9. [Assignments](https://claude.ai/chat/d1dafc33-fd56-416f-8da9-cf055355a9a5#9-assignments)

---

## 1. Users

### `POST /api/users/login/`

Authenticate a user and receive JWT tokens.

**Auth:** 🔓 Public

**Request body:**

```json
{
  "role":      "student | teacher | principal | admin",
  "school_id": "SCI-2024-001",
  "password":  "secret"
}
```

**Response `200`:**

```json
{
  "message":       "Login successful",
  "user_id":       1,
  "access_token":  "<jwt>",
  "refresh_token": "<jwt>"
}
```

**Errors:**

| Status  | Reason                                          |
| ------- | ----------------------------------------------- |
| `400` | Missing `role`,`school_id`, or `password` |
| `401` | Invalid credentials                             |
| `403` | Correct credentials but wrong role              |

---

### `GET /api/users/me/`

Return the authenticated user's profile. Response is cached per user.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "user": {
    "id":        1,
    "school_id": "SCI-2024-001",
    "role":      "student",
    "email":     "kwame@school.edu",
    "first_name":"Kwame",
    "last_name": "Asare"
  }
}
```

---

### `POST /api/users/logout/`

Invalidate the cached login token for the current user.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{ "message": "Logged out successfully" }
```

---

### `GET /api/users/`

List all users.

**Auth:** 👤 Any authenticated user (non-admin users only see their own record)

---

### `POST /api/users/`

Create a new user.

**Auth:** 🛡️ Admin

---

### `GET /api/users/{id}/`

Retrieve a single user.

**Auth:** 👤 Any authenticated user (non-admin users restricted to own record)

---

### `PUT /api/users/{id}/`

Full update of a user record.

**Auth:** 🛡️ Admin

---

### `PATCH /api/users/{id}/`

Partial update of a user record.

**Auth:** 🛡️ Admin

---

### `DELETE /api/users/{id}/`

Delete a user.

**Auth:** 🛡️ Admin

---

## 2. Students

### `GET /api/students/`

List students. Result set is scoped by role:

* **Admin / Staff** → all students
* **Teacher** → only students enrolled in their courses
* **Student** → only their own record

**Auth:** 👤 Any authenticated user

---

### `POST /api/students/`

Create a student profile.

**Auth:** 🛡️ Admin

---

### `GET /api/students/me/`

Return the authenticated student's own profile. Response is cached.

**Auth:** 🧑‍🎓 Student

**Response `200`:**

```json
{
  "id":             1,
  "student_number": "SCI-2024-001",
  "user":           { "first_name": "Kwame", "last_name": "Asare" },
  "programme":      { "id": 1, "name": "Science" },
  "level":          2
}
```

---

### `GET /api/students/by_programme/`

Filter students by programme and/or level. Response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param         | Type    | Description                        |
| ------------- | ------- | ---------------------------------- |
| `programme` | integer | Programme ID                       |
| `level`     | integer | Year level (e.g.`1`,`2`,`3`) |

**Response `200`:**

```json
{
  "total_students": 34,
  "students": [ { "...": "..." } ]
}
```

---

### `GET /api/students/{id}/`

Retrieve a single student.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/students/{id}/`

Full update of a student profile. Clears student cache on save.

**Auth:** 🛡️ Admin

---

### `PATCH /api/students/{id}/`

Partial update of a student profile. Clears student cache on save.

**Auth:** 🛡️ Admin

---

### `DELETE /api/students/{id}/`

Delete a student profile. Clears student cache before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/students/{id}/enrollments/`

List all active enrollments for a student. Response is cached.

**Auth:** 👤 Student (own record), Teacher (their enrolled students), Admin

**Response `200`:**

```json
{
  "student":           "SCI-2024-001",
  "student_name":      "Kwame Asare",
  "total_enrollments": 7,
  "enrollments": [ { "...": "..." } ]
}
```

---

### `GET /api/students/{id}/assignments/`

List all published assignments for a student's current-term enrollments. Response is cached.

**Auth:** 👤 Student (own record), Teacher (their enrolled students), Admin

**Response `200`:**

```json
{
  "student":           "SCI-2024-001",
  "total_assignments": 5,
  "assignments": [ { "...": "..." } ]
}
```

**Errors:**

| Status  | Reason                              |
| ------- | ----------------------------------- |
| `404` | No current academic term configured |

---

### `GET /api/students/{id}/submissions/`

List all submissions made by a student. Response is cached.

**Auth:** 👤 Student (own record), Teacher (their enrolled students), Admin

**Response `200`:**

```json
{
  "student":            "SCI-2024-001",
  "total_submissions":  12,
  "graded_submissions": 9,
  "submissions": [ { "...": "..." } ]
}
```

---

## 3. Teachers

### `GET /api/teachers/`

List teachers. Result set is scoped by role:

* **Admin / Staff** → all teachers
* **Teacher** → only their own record
* **Student** → only teachers of their enrolled courses

**Auth:** 👤 Any authenticated user

---

### `POST /api/teachers/`

Create a teacher profile.

**Auth:** 🛡️ Admin

---

### `GET /api/teachers/me/`

Return the authenticated teacher's own profile. Response is cached.

**Auth:** 👩‍🏫 Teacher

**Response `200`:**

```json
{
  "id":              1,
  "employee_number": "TCH-001",
  "user":            { "first_name": "Kweku", "last_name": "Asante" },
  "department":      "Mathematics"
}
```

---

### `GET /api/teachers/by_department/`

Filter teachers by department (case-insensitive partial match). Response is cached per department value.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param          | Type   | Description                             |
| -------------- | ------ | --------------------------------------- |
| `department` | string | Department name fragment (e.g.`math`) |

**Response `200`:**

```json
{
  "total_teachers": 8,
  "teachers": [ { "...": "..." } ]
}
```

---

### `GET /api/teachers/{id}/`

Retrieve a single teacher.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/teachers/{id}/`

Full update of a teacher profile. Clears teacher cache on save.

**Auth:** 🛡️ Admin

---

### `PATCH /api/teachers/{id}/`

Partial update of a teacher profile. Clears teacher cache on save.

**Auth:** 🛡️ Admin

---

### `DELETE /api/teachers/{id}/`

Delete a teacher profile. Clears teacher cache before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/teachers/{id}/courses/`

List all course offerings assigned to a teacher. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "teacher":         "Mr. Kweku Asante",
  "employee_number": "TCH-001",
  "total_courses":   3,
  "courses": [ { "...": "..." } ]
}
```

---

### `GET /api/teachers/{id}/assignments/`

List all assignments created by a teacher. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "teacher":           "Mr. Kweku Asante",
  "total_assignments": 14,
  "assignments": [ { "...": "..." } ]
}
```

---

### `GET /api/teachers/{id}/students/`

List all students enrolled in any of a teacher's courses. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "teacher":        "Mr. Kweku Asante",
  "total_students": 98,
  "students": [ { "...": "..." } ]
}
```

---

## 4. Principals

### `GET /api/principals/`

List principals.

**Auth:** 👤 Any authenticated user (non-admin users restricted to own record)

---

### `POST /api/principals/`

Create a principal profile.

**Auth:** 🛡️ Admin

---

### `GET /api/principals/me/`

Return the authenticated principal's own profile.

**Auth:** 🏫 Principal

---

### `GET /api/principals/dashboard/`

Return school-wide aggregate statistics. Response is cached and invalidated whenever students, assignments, or quizzes change.

**Auth:** 🏫 Principal

**Response `200`:**

```json
{
  "total_students":     1284,
  "total_teachers":     68,
  "total_programmes":   5,
  "active_assignments": 42,
  "active_quizzes":     18
}
```

---

### `GET /api/principals/{id}/`

Retrieve a single principal.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/principals/{id}/`

Full update of a principal profile.

**Auth:** 🛡️ Admin

---

### `PATCH /api/principals/{id}/`

Partial update of a principal profile.

**Auth:** 🛡️ Admin

---

### `DELETE /api/principals/{id}/`

Delete a principal profile.

**Auth:** 🛡️ Admin

---

## 5. Programmes

### `GET /api/programmes/`

List all programmes. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
[
  { "id": 1, "name": "Science" },
  { "id": 2, "name": "Business" },
  { "id": 3, "name": "General Arts" }
]
```

---

### `POST /api/programmes/`

Create a programme. Clears programme list and principal dashboard caches.

**Auth:** 🛡️ Admin

---

### `GET /api/programmes/{id}/`

Retrieve a single programme. Response is cached.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/programmes/{id}/`

Full update of a programme. Clears all programme-related caches.

**Auth:** 🛡️ Admin

---

### `PATCH /api/programmes/{id}/`

Partial update of a programme. Clears all programme-related caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/programmes/{id}/`

Delete a programme. Clears all programme-related caches before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/programmes/{id}/students/`

List all students enrolled in a programme. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "programme":      "Science",
  "total_students": 412,
  "students": [ { "...": "..." } ]
}
```

---

### `GET /api/programmes/{id}/electives/`

List elective courses available for a programme. When both `level` and `term` are supplied, returns active `CourseOffering` objects instead of bare `Course` objects. Response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param     | Type    | Description                         |
| --------- | ------- | ----------------------------------- |
| `level` | integer | Year level (e.g.`2`)              |
| `term`  | integer | Term number (`1`,`2`, or `3`) |

**Response `200` — without filters:**

```json
{
  "programme":       "Science",
  "total_electives": 6,
  "electives": [ { "id": 5, "name": "Physics" }, { "...": "..." } ]
}
```

**Response `200` — with `level` and `term`:**

```json
{
  "programme":           "Science",
  "level":               2,
  "term":                1,
  "available_electives": [ { "...": "..." } ]
}
```

**Errors:**

| Status  | Reason                                                                |
| ------- | --------------------------------------------------------------------- |
| `404` | `level`and `term`supplied but no current academic term configured |

---

## 6. Courses

### `GET /api/courses/`

List all courses. Supports filtering; response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param           | Type    | Description             |
| --------------- | ------- | ----------------------- |
| `course_type` | string  | `CORE`or `ELECTIVE` |
| `programme`   | integer | Programme ID            |

---

### `POST /api/courses/`

Create a course. Clears course list and programme list caches.

**Auth:** 🛡️ Admin

---

### `GET /api/courses/{id}/`

Retrieve a single course. Response is cached.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/courses/{id}/`

Full update of a course. Clears all course-related caches.

**Auth:** 🛡️ Admin

---

### `PATCH /api/courses/{id}/`

Partial update of a course. Clears all course-related caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/courses/{id}/`

Delete a course. Clears all course-related caches before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/courses/{id}/offerings/`

List active course offerings for a course. Supports filtering; response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param     | Type    | Description |
| --------- | ------- | ----------- |
| `level` | integer | Year level  |
| `term`  | integer | Term number |

**Response `200`:**

```json
{
  "course":          "Physics",
  "course_code":     "PHY",
  "total_offerings": 3,
  "offerings": [ { "...": "..." } ]
}
```

---

## 7. Course Offerings

### `GET /api/offerings/`

List course offerings. Result set is scoped by role:

* **Student** → offerings in the current term only
* **Teacher** → their own assigned offerings only (when no filters supplied)
* **Admin / Staff** → all offerings

Supports filtering; results are deduplicated.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param           | Type    | Description             |
| --------------- | ------- | ----------------------- |
| `level`       | integer | Year level              |
| `term`        | integer | Term number             |
| `course_type` | string  | `CORE`or `ELECTIVE` |
| `programme`   | integer | Programme ID            |

---

### `POST /api/offerings/`

Create a course offering.

**Auth:** 🛡️ Admin

---

### `GET /api/offerings/{id}/`

Retrieve a single course offering.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/offerings/{id}/`

Full update of a course offering. Clears offering and parent course caches.

**Auth:** 🛡️ Admin

---

### `PATCH /api/offerings/{id}/`

Partial update of a course offering. Clears offering and parent course caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/offerings/{id}/`

Delete a course offering. Clears offering and parent course caches before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/offerings/{id}/enrollments/`

List all active enrollments for a course offering. Response is cached. Only accessible to the teacher assigned to the offering or an admin.

**Auth:** 👩‍🏫 Teacher (assigned to offering), 🛡️ Admin

**Response `200`:**

```json
{
  "course_code":    "PHY2A",
  "course_name":    "Physics",
  "level":          2,
  "term":           1,
  "total_enrolled": 18,
  "enrollments": [ { "...": "..." } ]
}
```

**Errors:**

| Status  | Reason                                         |
| ------- | ---------------------------------------------- |
| `403` | Caller is not the assigned teacher or an admin |

---

### `GET /api/offerings/{id}/assignments/`

List assignments for a course offering. Students only see `PUBLISHED` assignments; teachers and admins see all statuses. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code":       "PHY2A",
  "course_name":       "Physics",
  "total_assignments": 4,
  "assignments": [ { "...": "..." } ]
}
```

---

### `GET /api/offerings/{id}/quizzes/`

List quizzes for a course offering. Students only see `PUBLISHED` quizzes; teachers and admins see all statuses. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code":   "PHY2A",
  "course_name":   "Physics",
  "total_quizzes": 2,
  "quizzes": [ { "...": "..." } ]
}
```

---

## 8. Enrollments

### `GET /api/enrollments/`

List enrollments. Result set is scoped by role:

* **Student** → their own active enrollments in the current term
* **Teacher** → enrollments for their assigned offerings
* **Admin / Staff** → all enrollments

**Auth:** 👤 Any authenticated user

---

### `POST /api/enrollments/`

Create a single enrollment. Clears student, offering, and assigned teacher caches.

**Auth:** 🛡️ Admin

---

### `GET /api/enrollments/my_enrollments/`

Return the authenticated student's current-term enrollments split into core and elective groups. Response is cached.

**Auth:** 🧑‍🎓 Student

**Response `200`:**

```json
{
  "term":             1,
  "academic_year":    "2025/2026",
  "core_courses":     [ { "...": "..." } ],
  "elective_courses": [ { "...": "..." } ],
  "total_courses":    7
}
```

**Errors:**

| Status  | Reason                              |
| ------- | ----------------------------------- |
| `403` | Caller is not a student             |
| `404` | No current academic term configured |

---

### `POST /api/enrollments/bulk_enroll/`

Enroll multiple students into a single course offering in one request. Invalidates each student's cache individually and the offering cache once after the loop.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "student_ids":        [1, 2, 3, 4],
  "course_offering_id": 12,
  "is_core":            false
}
```

**Response `201`:**

```json
{
  "message":        "Successfully enrolled 4 students",
  "enrolled_count": 4
}
```

**Errors:**

| Status  | Reason                                          |
| ------- | ----------------------------------------------- |
| `400` | `student_ids`or `course_offering_id`missing |
| `400` | One or more student IDs not found               |
| `404` | Course offering not found                       |

---

### `GET /api/enrollments/{id}/`

Retrieve a single enrollment.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/enrollments/{id}/`

Full update of an enrollment. Teachers may only update the `grade` field.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

### `PATCH /api/enrollments/{id}/`

Partial update of an enrollment. Teachers may only update the `grade` field.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

**Errors:**

| Status  | Reason                                                   |
| ------- | -------------------------------------------------------- |
| `403` | Teacher attempted to update a field other than `grade` |
| `403` | Teacher is not assigned to this offering                 |

---

### `DELETE /api/enrollments/{id}/`

Delete an enrollment. Clears student, offering, and teacher caches before deletion.

**Auth:** 🛡️ Admin

---

### `POST /api/enrollments/{id}/update_grade/`

Update the grade on a specific enrollment. Clears the student and offering caches after save.

**Auth:** 🛡️👩‍🏫 Teacher (assigned to offering) or Admin

**Request body:**

```json
{ "grade": "A" }
```

**Response `200`:** Updated enrollment object.

**Errors:**

| Status  | Reason                                   |
| ------- | ---------------------------------------- |
| `400` | `grade`field missing                   |
| `403` | Teacher is not assigned to this offering |
| `403` | Caller is neither a teacher nor an admin |

---

## 9. Assignments

### `GET /api/assignments/`

List assignments. Result set is scoped by role:

* **Teacher** → all assignments they created
* **Student** → only `PUBLISHED` assignments in their current-term enrolled offerings
* **Admin / Staff** → all assignments

**Auth:** 👤 Any authenticated user

---

### `POST /api/assignments/`

Create an assignment. The `teacher` field is set automatically from the authenticated user — it cannot be set by the client. Clears offering, teacher, and all enrolled students' assignment caches.

**Auth:** 👩‍🏫 Teacher

---

### `GET /api/assignments/{id}/`

Retrieve a single assignment.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/assignments/{id}/`

Full update of an assignment. Clears offering, teacher, and enrolled students' caches.

**Auth:** 👩‍🏫 Teacher (of this course), 🛡️ Admin

---

### `PATCH /api/assignments/{id}/`

Partial update of an assignment. Clears offering, teacher, and enrolled students' caches.

**Auth:** 👩‍🏫 Teacher (of this course), 🛡️ Admin

---

### `DELETE /api/assignments/{id}/`

Delete an assignment. Clears offering, teacher, and enrolled students' caches before deletion.

**Auth:** 👩‍🏫 Teacher (of this course), 🛡️ Admin

---

## Cache Behaviour Summary

All `GET` responses marked as *cached* are stored in Django's cache backend and invalidated automatically on related writes. Durations are defined centrally in `cache.py`.

| Data                                      | TTL                   |
| ----------------------------------------- | --------------------- |
| Login token                               | 4 h                   |
| User / Student / Teacher profile (`me`) | 5 h / 15 min / 15 min |
| Programmes, Courses (reference data)      | 30 min                |
| Enrollments, Assignments, Submissions     | 10 – 15 min          |
| Principal dashboard                       | 10 min                |
| Current academic term                     | 30 min                |

Cache keys follow the pattern `lms:<entity>:<id>:<sub-resource>`. To wipe the entire LMS cache namespace (e.g. after a bulk data migration):

```python
# requires django-redis
from django_redis import get_redis_connection
get_redis_connection("default").delete_pattern("lms:*")
```

---

## Common Error Responses

| Status                     | Meaning                                               |
| -------------------------- | ----------------------------------------------------- |
| `400 Bad Request`        | Missing or invalid request fields                     |
| `401 Unauthorized`       | Missing or expired JWT token                          |
| `403 Forbidden`          | Authenticated but insufficient role or ownership      |
| `404 Not Found`          | Resource does not exist or no current term configured |
| `405 Method Not Allowed` | HTTP method not supported on this endpoint            |
