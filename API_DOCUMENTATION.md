# LMS — API Documentation

**Base URL:** `/api/`

**Authentication:** JWT Bearer Token — include `Authorization: Bearer <access_token>` on every request except `POST /api/users/login/`.

**Content-Type:** `application/json`

---

## Role Abbreviations

| Symbol         | Role                      |
| -------------- | ------------------------- |
| 🔓             | Public (no auth required) |
| 👤             | Any authenticated user    |
| 🧑‍🎓         | Student only              |
| 👩‍🏫         | Teacher only              |
| 🏫             | Principal only            |
| 🛡️           | Admin only                |
| 🛡️👩‍🏫     | Teacher or Admin          |

---

## Table of Contents

1. [Users](#1-users)
2. [Students](#2-students)
3. [Teachers](#3-teachers)
4. [Principals](#4-principals)
5. [Admins](#5-admins)
6. [Academic Terms](#6-academic-terms)
7. [Programmes](#7-programmes)
8. [Courses](#8-courses)
9. [Course Offerings](#9-course-offerings)
10. [Enrollments](#10-enrollments)
11. [Assignments](#11-assignments)
12. [Submissions](#12-submissions)
13. [Quizzes](#13-quizzes)
14. [Questions](#14-questions)
15. [Choices](#15-choices)
16. [Answer Keys](#16-answer-keys)
17. [Grade Weights](#17-grade-weights)
18. [Cache Behaviour Summary](#cache-behaviour-summary)
19. [Common Error Responses](#common-error-responses)

---

## 1. Users

### `POST /api/users/login/`

Authenticate a user and receive JWT tokens.

**Auth:** 🔓 Public

**Request body:**

```json
{
  "role":      "student | teacher | principal | admin",
  "school_id": "STD001",
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

| Status | Reason                                        |
| ------ | --------------------------------------------- |
| `400`  | Missing `role`, `school_id`, or `password`    |
| `401`  | Invalid credentials                           |
| `403`  | Correct credentials but wrong role            |

---

### `GET /api/users/me/`

Return the authenticated user's profile. Response is cached per user for 5 hours.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "user": {
    "id":         1,
    "school_id":  "STD001",
    "role":       "student",
    "email":      "kwame@school.edu",
    "first_name": "Kwame",
    "last_name":  "Asare"
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

List all users. Non-admin users only see their own record.

**Auth:** 👤 Any authenticated user

---

### `POST /api/users/`

Create a new user.

**Auth:** 🛡️ Admin

---

### `GET /api/users/{id}/`

Retrieve a single user. Non-admin users are restricted to their own record.

**Auth:** 👤 Any authenticated user

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

### `POST /api/auth/token/`

Obtain a new JWT access/refresh token pair (SimpleJWT standard endpoint).

**Auth:** 🔓 Public

---

### `POST /api/auth/token/refresh/`

Refresh an access token using a valid refresh token. Rotates the refresh token and blacklists the old one.

**Auth:** 🔓 Public

---

### `POST /api/auth/token/blacklist/`

Blacklist a refresh token (logout via SimpleJWT).

**Auth:** 🔓 Public

---

## 2. Students

### `GET /api/students/`

List students. Result set is scoped by role:

- **Admin / Staff** → all students
- **Teacher** → only students enrolled in their courses
- **Student** → only their own record

**Auth:** 👤 Any authenticated user

---

### `POST /api/students/`

Create a student profile. A `student_number` (`STD001`, `STD002`, …) and `school_id` are auto-generated via a post-save signal.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "user": {
    "username":  "kwame.asare",
    "email":     "kwame@school.edu",
    "password":  "secret123",
    "password_confirm": "secret123",
    "first_name": "Kwame",
    "last_name":  "Asare"
  },
  "gender":       "male",
  "level":        1,
  "programme_id": 2
}
```

---

### `GET /api/students/me/`

Return the authenticated student's own profile. Response is cached for 15 minutes.

**Auth:** 🧑‍🎓 Student

**Response `200`:**

```json
{
  "id":             1,
  "student_number": "STD001",
  "full_name":      "Kwame Asare",
  "user":           { "email": "kwame@school.edu", "role": "student" },
  "programme":      "Science",
  "level":          1
}
```

---

### `GET /api/students/by_programme/`

Filter students by programme and/or level. Response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param       | Type    | Description                     |
| ----------- | ------- | ------------------------------- |
| `programme` | integer | Programme ID                    |
| `level`     | integer | Year level (`1`, `2`, or `3`)   |

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

List all active enrollments for a student. Response is cached for 15 minutes.

**Auth:** 👤 Student (own), Teacher (their enrolled students), Admin

**Response `200`:**

```json
{
  "student":           "STD001",
  "student_name":      "Kwame Asare",
  "total_enrollments": 7,
  "enrollments": [ { "...": "..." } ]
}
```

---

### `GET /api/students/{id}/assignments/`

List all published assignments for a student's current-term enrolled offerings. Response is cached for 10 minutes.

**Auth:** 👤 Student (own), Teacher (their enrolled students), Admin

**Response `200`:**

```json
{
  "student":           "STD001",
  "total_assignments": 5,
  "assignments": [ { "...": "..." } ]
}
```

**Errors:**

| Status | Reason                              |
| ------ | ----------------------------------- |
| `404`  | No current academic term configured |

---

### `GET /api/students/{id}/submissions/`

List all submissions made by a student. Response is cached for 10 minutes.

**Auth:** 👤 Student (own), Teacher (their enrolled students), Admin

**Response `200`:**

```json
{
  "student":            "STD001",
  "total_submissions":  12,
  "graded_submissions": 9,
  "submissions": [ { "...": "..." } ]
}
```

---

## 3. Teachers

### `GET /api/teachers/`

List teachers. Result set is scoped by role:

- **Admin / Staff** → all teachers
- **Teacher** → only their own record
- **Student** → only teachers of their enrolled courses

**Auth:** 👤 Any authenticated user

---

### `POST /api/teachers/`

Create a teacher profile. An `employee_number` (`TCH001`, `TCH002`, …) and `school_id` are auto-generated.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "user": {
    "username":  "kweku.asante",
    "email":     "kweku@school.edu",
    "password":  "secret123",
    "password_confirm": "secret123",
    "first_name": "Kweku",
    "last_name":  "Asante"
  },
  "department": "Mathematics"
}
```

---

### `GET /api/teachers/me/`

Return the authenticated teacher's own profile. Response is cached for 15 minutes.

**Auth:** 👩‍🏫 Teacher

**Response `200`:**

```json
{
  "id":              1,
  "employee_number": "TCH001",
  "full_name":       "Kweku Asante",
  "user":            { "email": "kweku@school.edu", "role": "teacher" },
  "department":      "Mathematics"
}
```

---

### `GET /api/teachers/by_department/`

Filter teachers by department (case-insensitive partial match). Response is cached per department value.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param        | Type   | Description                           |
| ------------ | ------ | ------------------------------------- |
| `department` | string | Department name fragment (e.g. `math`) |

**Response `200`:**

```json
{
  "total_teachers": 8,
  "teachers": [ { "...": "..." } ]
}
```

---

### `GET /api/teachers/{id}/`

Retrieve a single teacher. Access scoped by role.

**Auth:** 👤 Any authenticated user

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

List all course offerings assigned to a teacher. Response is cached for 15 minutes.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "teacher":         "Kweku Asante",
  "employee_number": "TCH001",
  "total_courses":   3,
  "courses": [ { "...": "..." } ]
}
```

---

### `GET /api/teachers/{id}/assignments/`

List all assignments created by a teacher. Response is cached for 10 minutes.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "teacher":           "Kweku Asante",
  "total_assignments": 14,
  "assignments": [ { "...": "..." } ]
}
```

---

### `GET /api/teachers/{id}/students/`

List all students enrolled in any of a teacher's courses. Response is cached for 15 minutes.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "teacher":        "Kweku Asante",
  "total_students": 98,
  "students": [ { "...": "..." } ]
}
```

---

## 4. Principals

### `GET /api/principals/`

List principals. Non-admin users restricted to their own record.

**Auth:** 👤 Any authenticated user

---

### `POST /api/principals/`

Create a principal profile. Sets `user.is_staff = true` automatically. An `employee_number` (`PRN001`, …) is auto-generated.

**Auth:** 🛡️ Admin

---

### `GET /api/principals/me/`

Return the authenticated principal's own profile.

**Auth:** 🏫 Principal

---

### `GET /api/principals/dashboard/`

Return school-wide aggregate statistics. Response is cached for 10 minutes and invalidated on student, assignment, or quiz changes.

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

## 5. Admins

### `GET /api/admins/`

List admin profiles. Non-admin users restricted to their own record.

**Auth:** 👤 Any authenticated user

---

### `POST /api/admins/`

Create an admin profile. Sets `user.is_staff = true` automatically. An `employee_number` (`ADM001`, …) is auto-generated.

**Auth:** 🛡️ Admin

---

### `GET /api/admins/me/`

Return the authenticated admin's own profile.

**Auth:** 🛡️ Admin

---

### `GET /api/admins/{id}/`

Retrieve a single admin.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/admins/{id}/` · `PATCH /api/admins/{id}/` · `DELETE /api/admins/{id}/`

**Auth:** 🛡️ Admin

---

## 6. Academic Terms

### `GET /api/terms/`

List all academic terms.

**Auth:** 👤 Any authenticated user

---

### `POST /api/terms/`

Create an academic term. If `is_current` is `true`, all other terms are atomically set to `is_current = false`. Clears the current-term and dashboard caches.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "name":                    "Term 1 2025/2026",
  "academic_year":           "2025/2026",
  "term_number":             1,
  "start_date":              "2025-09-01",
  "end_date":                "2025-12-15",
  "is_current":              true,
  "elective_selection_open": false
}
```

---

### `GET /api/terms/current/`

Return the active academic term.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "id":                      1,
  "name":                    "Term 1 2025/2026",
  "academic_year":           "2025/2026",
  "term_number":             1,
  "start_date":              "2025-09-01",
  "end_date":                "2025-12-15",
  "is_current":              true,
  "elective_selection_open": false
}
```

**Errors:**

| Status | Reason                              |
| ------ | ----------------------------------- |
| `404`  | No current academic term configured |

---

### `GET /api/terms/{id}/`

Retrieve a single term.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/terms/{id}/` · `PATCH /api/terms/{id}/`

Update a term. Clears current-term and dashboard caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/terms/{id}/`

Delete a term. Clears current-term and dashboard caches.

**Auth:** 🛡️ Admin

---

## 7. Programmes

### `GET /api/programmes/`

List all programmes. Response is cached for 30 minutes.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
[
  { "id": 1, "name": "Science",      "code": "SCI", "max_electives_per_term": 4 },
  { "id": 2, "name": "Business",     "code": "BUS", "max_electives_per_term": 4 },
  { "id": 3, "name": "General Arts", "code": "GEN", "max_electives_per_term": 4 }
]
```

---

### `POST /api/programmes/`

Create a programme. Clears programme list and principal dashboard caches.

**Auth:** 🛡️ Admin

---

### `GET /api/programmes/{id}/`

Retrieve a single programme. Response is cached for 30 minutes.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/programmes/{id}/` · `PATCH /api/programmes/{id}/`

Update a programme. Clears all programme-related caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/programmes/{id}/`

Delete a programme. Clears all programme-related caches before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/programmes/{id}/students/`

List all students enrolled in a programme. Response is cached for 30 minutes.

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

| Param   | Type    | Description                      |
| ------- | ------- | -------------------------------- |
| `level` | integer | Year level (e.g. `2`)            |
| `term`  | integer | Term number (`1`, `2`, or `3`)   |

**Response `200` — without filters:**

```json
{
  "programme":       "Science",
  "total_electives": 6,
  "electives": [ { "id": 5, "name": "Physics" } ]
}
```

**Response `200` — with `level` and `term`:**

```json
{
  "programme":           "Science",
  "level":               2,
  "term":                1,
  "available_electives": [ { "id": 8, "course_code": "PHY201" } ]
}
```

**Errors:**

| Status | Reason                                                              |
| ------ | ------------------------------------------------------------------- |
| `404`  | `level` and `term` supplied but no current academic term configured |

---

## 8. Courses

### `GET /api/courses/`

List all courses. Supports filtering; response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param         | Type    | Description              |
| ------------- | ------- | ------------------------ |
| `course_type` | string  | `CORE` or `ELECTIVE`     |
| `programme`   | integer | Programme ID             |

---

### `POST /api/courses/`

Create a course. Clears course list and programme list caches.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "name":          "Mathematics",
  "code_prefix":   "MTH",
  "course_type":   "CORE",
  "credits":       3,
  "programme_ids": [1, 2]
}
```

---

### `GET /api/courses/{id}/`

Retrieve a single course. Response is cached.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/courses/{id}/` · `PATCH /api/courses/{id}/`

Update a course. Clears all course-related caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/courses/{id}/`

Delete a course and all its offerings. Clears caches before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/courses/{id}/offerings/`

List active course offerings for a course. Supports optional level/term filtering. Response is cached per filter combination.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param   | Type    | Description |
| ------- | ------- | ----------- |
| `level` | integer | Year level  |
| `term`  | integer | Term number |

**Response `200`:**

```json
{
  "course":          "Mathematics",
  "course_code":     "MTH",
  "total_offerings": 3,
  "offerings": [ { "id": 1, "course_code": "MTH101" } ]
}
```

---

## 9. Course Offerings

### `GET /api/offerings/`

List course offerings. Result set is scoped by role:

- **Student** → current-term offerings only
- **Teacher** → their assigned offerings only
- **Admin / Staff** → all offerings

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param         | Type    | Description            |
| ------------- | ------- | ---------------------- |
| `level`       | integer | Year level             |
| `term`        | integer | Term number            |
| `course_type` | string  | `CORE` or `ELECTIVE`   |
| `programme`   | integer | Programme ID           |

---

### `POST /api/offerings/`

Create a course offering.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "course": 3,
  "level":  1,
  "term":   1,
  "weeks":  "12",
  "room":   "A101"
}
```

---

### `GET /api/offerings/{id}/`

Retrieve a single course offering.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "id":          1,
  "course_code": "MTH101",
  "course":      3,
  "level":       1,
  "term":        1,
  "is_active":   true,
  "weeks":       "12",
  "room":        "A101",
  "progress":    42,
  "teachers":    ["Kweku Asante"]
}
```

---

### `PUT /api/offerings/{id}/` · `PATCH /api/offerings/{id}/`

Update a course offering. Clears offering and parent course caches.

**Auth:** 🛡️ Admin

---

### `DELETE /api/offerings/{id}/`

Delete a course offering. Clears offering and parent course caches before deletion.

**Auth:** 🛡️ Admin

---

### `GET /api/offerings/{id}/enrollments/`

List all active enrollments for a course offering. Response is cached. Only the assigned teacher or an admin can access this.

**Auth:** 👩‍🏫 Teacher (assigned), 🛡️ Admin

**Response `200`:**

```json
{
  "course_code":    "MTH101",
  "course_name":    "Mathematics",
  "level":          1,
  "term":           1,
  "total_enrolled": 32,
  "enrollments": [
    {
      "student":  "STD001",
      "teacher":  "Kweku Asante",
      "room":     "A101",
      "schedule": [
        { "day": "monday",    "start_time": "08:00", "end_time": "09:00" },
        { "day": "wednesday", "start_time": "08:00", "end_time": "09:00" }
      ]
    }
  ]
}
```

**Errors:**

| Status | Reason                                         |
| ------ | ---------------------------------------------- |
| `403`  | Caller is not the assigned teacher or an admin |

---

### `GET /api/offerings/{id}/assignments/`

List assignments for a course offering. Students only see `PUBLISHED` assignments; teachers/admins see all statuses. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code":       "MTH101",
  "course_name":       "Mathematics",
  "total_assignments": 4,
  "assignments": [ { "...": "..." } ]
}
```

---

### `GET /api/offerings/{id}/quizzes/`

List quizzes for a course offering. Students only see `PUBLISHED` quizzes. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code":   "MTH101",
  "course_name":   "Mathematics",
  "total_quizzes": 2,
  "quizzes": [ { "...": "..." } ]
}
```

---

### `GET /api/offerings/{id}/outline/`

Return the week-by-week course outline with the current progress percentage. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code": "MTH101",
  "course_name": "Mathematics",
  "total_weeks": 12,
  "progress":    42,
  "weeks": [
    {
      "id":          1,
      "week":        1,
      "title":       "Introduction to Algebra",
      "description": "...",
      "topics":      ["Variables", "Expressions"],
      "status":      "completed"
    }
  ]
}
```

---

### `GET /api/offerings/{id}/resources/`

List all course resources (files, links, videos) for a course offering. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code":     "MTH101",
  "course_name":     "Mathematics",
  "total_resources": 8,
  "resources": [
    {
      "id":          1,
      "title":       "Week 1 Slides",
      "type":        "pptx",
      "url":         "",
      "file":        "<presigned-s3-url>",
      "uploaded_at": "2025-09-05T10:00:00Z"
    }
  ]
}
```

---

### `GET /api/offerings/{id}/stats/`

Return aggregate stats for a course offering. For students, includes their current enrollment grade. Response is cached.

**Auth:** 👤 Any authenticated user

**Response `200`:**

```json
{
  "course_code": "MTH101",
  "progress":    42,
  "grade":       "B+",
  "assignments": 4,
  "quizzes":     2
}
```

---

### `GET /api/offerings/{id}/gradebook/`

Return the full grade breakdown for the authenticated student in a given course offering. Computes weighted assignment and quiz scores, then maps to a letter grade. Response is cached per student per offering for 5 minutes.

**Auth:** 🧑‍🎓 Student

**Response `200`:**

```json
{
  "course_code": "MTH101",
  "course_name": "Mathematics",
  "weights": {
    "assignments": 50,
    "quizzes":     50,
    "total":       100
  },
  "summary": {
    "assignment_score": 78.5,
    "quiz_score":       82.0,
    "overall_score":    80.25,
    "letter_grade":     "A"
  },
  "entries": [
    {
      "id":             1,
      "category":       "Assignment",
      "title":          "Week 3 Problem Set",
      "total_marks":    100,
      "marks_obtained": 85,
      "percentage":     85.0,
      "status":         "graded"
    },
    {
      "id":             2,
      "category":       "Quiz",
      "title":          "Algebra Quiz",
      "total_marks":    50,
      "marks_obtained": 41,
      "percentage":     82.0,
      "status":         "graded"
    }
  ]
}
```

**Letter grade scale:**

| Score   | Grade |
| ------- | ----- |
| ≥ 80    | A     |
| ≥ 75    | B+    |
| ≥ 70    | B     |
| ≥ 65    | C+    |
| ≥ 60    | C     |
| ≥ 55    | D+    |
| ≥ 50    | D     |
| ≥ 45    | E     |
| < 45    | F     |

**Errors:**

| Status | Reason                     |
| ------ | -------------------------- |
| `403`  | Caller is not a student    |

---

## 10. Enrollments

### `GET /api/enrollments/`

List enrollments. Result set is scoped by role:

- **Student** → their own active enrollments in the current term
- **Teacher** → enrollments for their assigned offerings
- **Admin / Staff** → all enrollments

**Auth:** 👤 Any authenticated user

---

### `POST /api/enrollments/`

Create a single enrollment. Auto-assigns the correct `teaching_slot` based on the student's section (core) or the sole slot for electives. Clears student, offering, and teacher caches.

**Auth:** 🛡️ Admin

**Request body:**

```json
{
  "student":          1,
  "course_offering":  5,
  "is_core":          true
}
```

---

### `GET /api/enrollments/my_enrollments/`

Return the authenticated student's current-term enrollments split into core and elective groups. Includes teacher name, room, and weekly schedule per enrollment. Response is cached for 10 minutes.

**Auth:** 🧑‍🎓 Student

**Response `200`:**

```json
{
  "term":             1,
  "academic_year":    "2025/2026",
  "core_courses": [
    {
      "course_code": "MTH101",
      "teacher":     "Kweku Asante",
      "room":        "A101",
      "schedule": [
        { "day": "monday", "start_time": "08:00", "end_time": "09:00" }
      ]
    }
  ],
  "elective_courses": [ { "...": "..." } ],
  "total_courses":    7
}
```

**Errors:**

| Status | Reason                              |
| ------ | ----------------------------------- |
| `403`  | Caller is not a student             |
| `404`  | No current academic term configured |

---

### `POST /api/enrollments/select_electives/`

Allow a student to self-enroll in elective course offerings. Gated by `AcademicTerm.elective_selection_open` and the programme's `max_electives_per_term`.

**Auth:** 🧑‍🎓 Student

**Request body:**

```json
{ "course_offering_ids": [8, 9] }
```

**Response `200`:**

```json
{
  "message":  "Successfully enrolled in 2 elective(s)",
  "enrolled": [ { "id": 8, "course_code": "PHY101" }, { "...": "..." } ]
}
```

**Errors:**

| Status | Reason                                               |
| ------ | ---------------------------------------------------- |
| `400`  | `course_offering_ids` missing or empty               |
| `400`  | Duplicate IDs in the list                            |
| `400`  | Elective selection is currently closed               |
| `400`  | Offering level does not match the student's level    |
| `400`  | Max electives per term already reached               |
| `400`  | Student already enrolled in one of the offerings     |
| `400`  | Course is not listed as an elective for the programme|

---

### `POST /api/enrollments/bulk_enroll/`

Enroll multiple students into a single course offering in one request. Skips already-enrolled students. Invalidates each student's cache individually; offering cache is invalidated once after the loop.

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

| Status | Reason                                               |
| ------ | ---------------------------------------------------- |
| `400`  | `student_ids` or `course_offering_id` missing        |
| `400`  | One or more student IDs not found                    |
| `404`  | Course offering not found                            |

---

### `GET /api/enrollments/{id}/`

Retrieve a single enrollment.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/enrollments/{id}/` · `PATCH /api/enrollments/{id}/`

Update an enrollment. Teachers may only update the `grade` field.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

**Errors:**

| Status | Reason                                              |
| ------ | --------------------------------------------------- |
| `403`  | Teacher attempted to update a field other than `grade` |
| `403`  | Teacher is not assigned to this offering            |

---

### `DELETE /api/enrollments/{id}/`

Delete an enrollment. Clears student, offering, and teacher caches before deletion.

**Auth:** 🛡️ Admin

---

### `POST /api/enrollments/{id}/update_grade/`

Update the final grade on a specific enrollment. Clears the student and offering caches after save.

**Auth:** 🛡️👩‍🏫 Teacher (assigned to offering) or Admin

**Request body:**

```json
{ "grade": "A" }
```

**Response `200`:** Updated enrollment object.

**Errors:**

| Status | Reason                                     |
| ------ | ------------------------------------------ |
| `400`  | `grade` field missing                      |
| `403`  | Teacher is not assigned to this offering   |
| `403`  | Caller is neither a teacher nor an admin   |

---

## 11. Assignments

### `GET /api/assignments/`

List assignments. Result set is scoped by role:

- **Teacher** → all assignments they created
- **Student** → only `PUBLISHED` assignments in their current-term enrolled offerings
- **Admin / Staff** → all assignments

Every assignment includes `submission_count` and `graded_submission_count`, computed efficiently via DB annotation.

**Auth:** 👤 Any authenticated user

---

### `POST /api/assignments/`

Create an assignment. The `teacher` is set automatically to the requesting user. Clears offering, teacher, and all enrolled students' assignment caches.

**Auth:** 👩‍🏫 Teacher

**Request body:**

```json
{
  "course_offering": 5,
  "title":           "Week 3 Problem Set",
  "description":     "Solve questions 1–20 from chapter 3.",
  "status":          "draft",
  "total_marks":     100,
  "due_date":        "2025-10-15T23:59:00Z",
  "max_attempts":    2
}
```

---

### `GET /api/assignments/{id}/`

Retrieve a single assignment.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/assignments/{id}/` · `PATCH /api/assignments/{id}/`

Update an assignment. Clears offering, teacher, and enrolled students' caches.

**Auth:** 👩‍🏫 Teacher (of this course), 🛡️ Admin

---

### `DELETE /api/assignments/{id}/`

Delete an assignment. Clears offering, teacher, and enrolled students' caches before deletion.

**Auth:** 👩‍🏫 Teacher (of this course), 🛡️ Admin

---

## 12. Submissions

### `GET /api/submissions/`

List submissions. Result set is scoped by role:

- **Student** → only their own submissions
- **Teacher** → submissions for their assignments
- **Admin / Staff** → all submissions

Supports optional `assignment` query parameter to filter by assignment ID.

**Auth:** 👤 Any authenticated user

**Query parameters:**

| Param        | Type    | Description   |
| ------------ | ------- | ------------- |
| `assignment` | integer | Assignment ID |

---

### `POST /api/submissions/`

Submit an assignment. `student` is set automatically from the requesting user. Enforces attempt limits, due-date, and requires at least one of `text_answer` or `file`. Clears student and offering caches.

**Auth:** 🧑‍🎓 Student

**Request body:**

```json
{
  "assignment":   5,
  "text_answer":  "My solution is...",
  "file":         "<multipart file upload>"
}
```

**Response `201`:** Created submission object including `attempt_number`.

**Errors:**

| Status | Reason                                              |
| ------ | --------------------------------------------------- |
| `400`  | Neither `text_answer` nor `file` provided           |
| `400`  | Assignment is past its due date                     |
| `400`  | Maximum attempt count reached                       |
| `400`  | Marks validation failure (on update)                |

---

### `GET /api/submissions/{id}/`

Retrieve a single submission.

**Auth:** 👤 Any authenticated user (access scoped by role)

---

### `PUT /api/submissions/{id}/` · `PATCH /api/submissions/{id}/`

Update a submission. Students cannot update grading fields (`marks_obtained`, `feedback`, `is_graded`, `graded_at`, `graded_by`, `status`). Students cannot update a submission after the due date.

**Auth:** 👤 Owner (student), 🛡️ Admin

---

### `DELETE /api/submissions/{id}/`

Delete a submission.

**Auth:** 🛡️ Admin

---

### `POST /api/submissions/{id}/grade/`

Grade a submission. Sets `is_graded`, `marks_obtained`, `graded_at`, and `graded_by` automatically.

**Auth:** 👩‍🏫 Teacher (of this assignment), 🛡️ Admin

**Request body:**

```json
{
  "marks_obtained": 88,
  "feedback":       "Good work, but review question 5.",
  "status":         "graded"
}
```

The `status` field accepts `"graded"` or `"returned"` (returned means the teacher sent it back for revision).

**Errors:**

| Status | Reason                                             |
| ------ | -------------------------------------------------- |
| `400`  | `marks_obtained` required when status is `graded`  |
| `400`  | `marks_obtained` exceeds `total_marks`             |
| `400`  | Invalid `status` value                             |
| `403`  | Caller is not the assignment's teacher or an admin |

---

## 13. Quizzes

### `GET /api/quizzes/`

List quizzes. Result set is scoped by role:

- **Teacher** → quizzes they created
- **Student** → `PUBLISHED` quizzes in their current-term offerings, with `attempts_used` and `attempts_remaining` fields per quiz
- **Admin / Staff** → all quizzes

**Auth:** 👤 Any authenticated user

---

### `POST /api/quizzes/`

Create a quiz. `teacher` is set automatically. Clears offering and student quiz caches.

**Auth:** 👩‍🏫 Teacher

**Request body:**

```json
{
  "course_offering":  5,
  "title":            "Chapter 3 Quiz",
  "description":      "Covers sections 3.1–3.4.",
  "duration_minutes": 30,
  "max_attempts":     1,
  "start_time":       "2025-10-10T09:00:00Z",
  "end_time":         "2025-10-10T10:00:00Z",
  "reveal_grade":     true
}
```

---

### `GET /api/quizzes/{id}/`

Retrieve a quiz. Teachers and admins see correct answers. Students see questions without `is_correct` or answer keys. Response is cached.

**Auth:** 👤 Any authenticated user

---

### `PUT /api/quizzes/{id}/` · `PATCH /api/quizzes/{id}/`

Update a quiz. Clears quiz and offering caches.

**Auth:** 👩‍🏫 Teacher (owner), 🛡️ Admin

---

### `DELETE /api/quizzes/{id}/`

Delete a quiz. Clears quiz and offering caches.

**Auth:** 👩‍🏫 Teacher (owner), 🛡️ Admin

---

### `GET /api/quizzes/{id}/questions/`

List all questions for a quiz. Response is cached. Answer information is stripped for students.

**Auth:** 👤 Any authenticated user

---

### `POST /api/quizzes/{id}/publish/`

Publish a quiz (set status to `PUBLISHED`). Quiz must be in `draft` status. Clears quiz and offering caches.

**Auth:** 👩‍🏫 Teacher (owner), 🛡️ Admin

**Response `200`:**

```json
{ "message": "Quiz published", "status": "published" }
```

---

### `POST /api/quizzes/{id}/close/`

Close a quiz (set status to `CLOSED`). Clears quiz and offering caches.

**Auth:** 👩‍🏫 Teacher (owner), 🛡️ Admin

**Response `200`:**

```json
{ "message": "Quiz closed", "status": "closed" }
```

---

### `GET /api/quizzes/{id}/attempts/`

List all student attempts for a quiz (teacher overview). Response is cached for 10 minutes.

**Auth:** 👩‍🏫 Teacher (owner), 🛡️ Admin

**Response `200`:**

```json
{
  "quiz":         "Chapter 3 Quiz",
  "total_marks":  50,
  "total_attempts": 28,
  "attempts": [ { "...": "..." } ]
}
```

---

### `POST /api/quizzes/{id}/start/`

Open a new quiz attempt for the authenticated student. Enforces `max_attempts` and checks that the quiz is published and within its time window.

**Auth:** 🧑‍🎓 Student

**Response `201`:**

```json
{
  "attempt_id":   3,
  "started_at":   "2025-10-10T09:05:00Z",
  "time_limit":   30,
  "questions": [
    {
      "id":            12,
      "question":      "What is 2 + 2?",
      "question_type": "mcq_single",
      "marks":         5,
      "choices": [
        { "id": 45, "answer": "3", "order": 1 },
        { "id": 46, "answer": "4", "order": 2 }
      ]
    }
  ]
}
```

**Errors:**

| Status | Reason                                      |
| ------ | ------------------------------------------- |
| `400`  | Quiz is not published                       |
| `400`  | Quiz is past its end time                   |
| `400`  | Maximum attempts already reached            |
| `400`  | An in-progress attempt already exists       |

---

### `POST /api/quizzes/{id}/submit/`

Submit answers for a quiz attempt. Auto-grades MCQ single, MCQ multiple (partial marks), true/false, and short-answer questions. Short-answer questions requiring manual grading remain with `marks_awarded = null`.

**Auth:** 🧑‍🎓 Student

**Request body:**

```json
{
  "attempt_id": 3,
  "answers": [
    { "question": 12, "selected_choice":  46 },
    { "question": 13, "selected_choices": [49, 51] },
    { "question": 14, "text_answer": "Photosynthesis" }
  ]
}
```

**Response `200`:**

```json
{
  "message":       "Quiz submitted successfully",
  "attempt_id":    3,
  "auto_graded":   true,
  "marks_obtained": 45,
  "total_marks":   50
}
```

**Errors:**

| Status | Reason                                      |
| ------ | ------------------------------------------- |
| `400`  | `attempt_id` missing or invalid             |
| `400`  | Attempt does not belong to this student     |
| `400`  | Attempt is already submitted                |
| `400`  | Time limit exceeded                         |

---

### `GET /api/quizzes/{id}/result/`

Return the best attempt result for the authenticated student. Only available when the quiz has `reveal_grade = true`.

**Auth:** 🧑‍🎓 Student

**Response `200`:**

```json
{
  "attempt_id":    3,
  "marks_obtained": 45,
  "total_marks":   50,
  "percentage":    90.0,
  "status":        "graded"
}
```

**Errors:**

| Status | Reason                          |
| ------ | ------------------------------- |
| `403`  | `reveal_grade` is `false`       |
| `404`  | No submitted attempt found      |

---

### `GET /api/quizzes/{id}/review/`

Return the attempt with full answer review (correct choices and explanations revealed). Only available after submission and when `reveal_grade = true`.

**Auth:** 🧑‍🎓 Student

---

### `POST /api/quizzes/{id}/grade/`

Manually grade one or more short-answer questions in a quiz attempt. Supports partial overrides.

**Auth:** 👩‍🏫 Teacher (owner), 🛡️ Admin

**Request body:**

```json
{
  "attempt_id": 3,
  "answer_grades": [
    { "answer_id": 201, "marks_awarded": 4 },
    { "answer_id": 202, "marks_awarded": 3 }
  ]
}
```

**Response `200`:** Updated attempt object with recalculated `marks_obtained`.

**Errors:**

| Status | Reason                                          |
| ------ | ----------------------------------------------- |
| `400`  | `attempt_id` or `answer_grades` missing         |
| `400`  | `marks_awarded` exceeds question's `marks`      |
| `404`  | Attempt or answer ID not found                  |

---

## 14. Questions

Questions can only be created, updated, or deleted while the parent quiz is in `draft` status.

### `GET /api/questions/`

List questions. Teachers see only their own quiz questions; admins see all.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

### `POST /api/questions/`

Add a question to a draft quiz.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

**Request body:**

```json
{
  "quiz":          5,
  "question":      "What is the capital of Ghana?",
  "question_type": "mcq_single",
  "marks":         5,
  "order":         1,
  "explanation":   "Accra is the capital.",
  "is_required":   true
}
```

**Question types:** `mcq_single`, `mcq_multiple`, `true_false`, `short_answer`

---

### `GET /api/questions/{id}/`

Retrieve a single question with its choices and answer keys.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

### `PUT /api/questions/{id}/` · `PATCH /api/questions/{id}/`

Update a question. Only allowed while quiz is in `draft` status.

**Auth:** 🛡️👩‍🏫 Teacher (owner), Admin

---

### `DELETE /api/questions/{id}/`

Delete a question. Only allowed while quiz is in `draft` status.

**Auth:** 🛡️👩‍🏫 Teacher (owner), Admin

---

## 15. Choices

Choices belong to `mcq_single`, `mcq_multiple`, or `true_false` questions. Short-answer questions must not have choices.

### `GET /api/choices/`

List choices. Scoped to the teacher's own quiz questions.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

### `POST /api/choices/`

Add a choice to a question. Only allowed while quiz is in `draft` status. Validates:

- `mcq_single` → exactly one choice can have `is_correct = true`
- `true_false` → max 2 choices, answers must be `"True"` / `"False"`
- `short_answer` → no choices allowed

**Auth:** 🛡️👩‍🏫 Teacher or Admin

**Request body:**

```json
{
  "question":  12,
  "answer":    "Accra",
  "is_correct": true,
  "order":     1
}
```

---

### `GET /api/choices/{id}/` · `PUT /api/choices/{id}/` · `PATCH /api/choices/{id}/` · `DELETE /api/choices/{id}/`

Standard CRUD. All mutations only allowed while quiz is in `draft` status.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

## 16. Answer Keys

Answer keys are used for auto-grading `short_answer` questions. Each key is a normalised (lowercased, trimmed) accepted answer string.

### `GET /api/answer-keys/`

List answer keys. Scoped to the teacher's own quiz questions.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

### `POST /api/answer-keys/`

Add an accepted answer for a short-answer question.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

**Request body:**

```json
{
  "question": 14,
  "text":     "Photosynthesis"
}
```

The `text` is stored as lowercase. Duplicate keys per question are rejected.

---

### `GET /api/answer-keys/{id}/` · `PUT /api/answer-keys/{id}/` · `PATCH /api/answer-keys/{id}/` · `DELETE /api/answer-keys/{id}/`

Standard CRUD.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

## 17. Grade Weights

Each course offering can have one `GradeWeight` record that controls the assignment/quiz weighting used in the gradebook calculation.

### `GET /api/grade-weights/`

List grade weights. Teachers see weights for their assigned offerings; admins see all.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

---

### `POST /api/grade-weights/`

Create grade weights for a course offering. Only one record is allowed per offering.

**Auth:** 🛡️👩‍🏫 Teacher or Admin

**Request body:**

```json
{
  "course_offering":    5,
  "assignments_weight": 60,
  "quizzes_weight":     40
}
```

**Errors:**

| Status | Reason                                              |
| ------ | --------------------------------------------------- |
| `400`  | Grade weights already exist for this course offering |

---

### `GET /api/grade-weights/{id}/` · `PUT /api/grade-weights/{id}/` · `PATCH /api/grade-weights/{id}/`

Retrieve or update grade weights. Cache for the parent offering is cleared on update.

**Auth:** 🛡️👩‍🏫 Teacher (assigned), Admin

---

### `DELETE /api/grade-weights/{id}/`

Delete grade weights. Offering cache is cleared.

**Auth:** 🛡️👩‍🏫 Teacher (assigned), Admin

---

## Cache Behaviour Summary

All `GET` responses marked as *cached* are stored in Redis and invalidated automatically on related writes. TTL constants are defined in `core/cache.py`. All cache keys share the `lms:` namespace prefix.

| Data                                    | TTL         |
| --------------------------------------- | ----------- |
| Login token                             | 4 h         |
| User `me`                               | 5 h         |
| Student / Teacher profile               | 15 min      |
| Programmes, Courses (reference data)    | 30 min      |
| Current academic term                   | 30 min      |
| Enrollments, Assignments, Submissions   | 10–15 min   |
| Quiz detail / attempts                  | 10 min      |
| Offering stats / outline / resources    | 10 min      |
| Gradebook (per student per offering)    | 5 min       |
| Principal dashboard                     | 10 min      |

To wipe the entire LMS cache namespace (e.g. after a bulk data migration):

```python
from django_redis import get_redis_connection
get_redis_connection("default").delete_pattern("lms:*")
```

---

## Common Error Responses

| Status                   | Meaning                                               |
| ------------------------ | ----------------------------------------------------- |
| `400 Bad Request`        | Missing or invalid request fields                     |
| `401 Unauthorized`       | Missing or expired JWT token                          |
| `403 Forbidden`          | Authenticated but insufficient role or ownership      |
| `404 Not Found`          | Resource does not exist or no current term configured |
| `405 Method Not Allowed` | HTTP method not supported on this endpoint            |
