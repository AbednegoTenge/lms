"""
cache.py
========
Single source of truth for every caching concern in the LMS app:

  • CACHE_TTL   – all expiry durations in one place
  • CacheKeys   – deterministic, namespaced key builders
  • invalidate_* – high-level invalidation helpers used by viewsets

Import pattern in views.py
--------------------------
    from .cache import CACHE_TTL, CacheKeys
    from .cache import (
        invalidate_student_cache,
        invalidate_teacher_cache,
        invalidate_offering_cache,
        invalidate_programme_cache,
        invalidate_course_cache,
    )
"""

from django.core.cache import cache


# ==================== TTL CONSTANTS ====================
# All durations are in seconds.
# Tune here without touching any viewset code.

CACHE_TTL = {
    # ── Auth ──────────────────────────────────────────
    "login":                60 * 60 * 4,    # 4 h  – matches JWT access window
    "user_me":              60 * 60 * 5,    # 5 h

    # ── Slow-changing reference data ──────────────────
    "current_term":         60 * 30,        # 30 min
    "programme_list":       60 * 30,
    "programme_detail":     60 * 30,
    "programme_students":   60 * 30,
    "programme_electives":  60 * 30,
    "course_list":          60 * 30,
    "course_detail":        60 * 30,
    "course_offerings":     60 * 30,

    # ── Per-user operational data ─────────────────────
    "student_me":           60 * 15,        # 15 min
    "student_enrollments":  60 * 15,
    "student_assignments":  60 * 10,        # 10 min
    "student_submissions":  60 * 10,
    "student_by_programme": 60 * 15,

    "teacher_me":           60 * 15,
    "teacher_courses":      60 * 15,
    "teacher_assignments":  60 * 10,
    "teacher_students":     60 * 15,
    "teacher_by_dept":      60 * 15,

    "principal_dashboard":  60 * 10,

    "offering_enrollments": 60 * 10,
    "offering_assignments": 60 * 10,
    "offering_quizzes":     60 * 10,

    "my_enrollments":       60 * 10,
}


# ==================== CACHE KEY BUILDERS ====================

class CacheKeys:
    """
    Deterministic, namespaced cache key factory.

    All keys share the ``lms:`` prefix so the entire LMS cache can be
    bulk-wiped in one call if you use a pattern-aware backend::

        # django-redis
        from django_redis import get_redis_connection
        get_redis_connection("default").delete_pattern("lms:*")

    Key structure convention:
        lms:<entity>:<id>:<sub-resource>[:<qualifiers>]
    """

    # ── Auth ──────────────────────────────────────────────────────────────────

    @staticmethod
    def login(role: str, school_id: str) -> str:
        """Cached JWT payload produced after a successful login."""
        return f"lms:login:{role}:{school_id}"

    @staticmethod
    def user_me(user_id: int) -> str:
        """Serialized User record for the /users/me/ endpoint."""
        return f"lms:user_me:{user_id}"

    # ── Academic term ─────────────────────────────────────────────────────────

    @staticmethod
    def current_term() -> str:
        """The single active AcademicTerm object (school-wide singleton)."""
        return "lms:current_term"

    # ── Programme ─────────────────────────────────────────────────────────────

    @staticmethod
    def programme_list() -> str:
        return "lms:programme:list"

    @staticmethod
    def programme_detail(pk) -> str:
        return f"lms:programme:{pk}"

    @staticmethod
    def programme_students(pk) -> str:
        return f"lms:programme:{pk}:students"

    @staticmethod
    def programme_electives(pk, level=None, term=None) -> str:
        """
        Parameterised key so filtered and unfiltered results are cached
        independently without colliding.
        """
        suffix = f":{level}:{term}" if (level is not None and term is not None) else ""
        return f"lms:programme:{pk}:electives{suffix}"

    # ── Course ────────────────────────────────────────────────────────────────

    @staticmethod
    def course_list(course_type=None, programme_id=None) -> str:
        """List key varies by the two supported filter params."""
        return f"lms:course:list:{course_type}:{programme_id}"

    @staticmethod
    def course_detail(pk) -> str:
        return f"lms:course:{pk}"

    @staticmethod
    def course_offerings(pk, level=None, term=None) -> str:
        return f"lms:course:{pk}:offerings:{level}:{term}"

    # ── Student ───────────────────────────────────────────────────────────────

    @staticmethod
    def student_me(user_id: int) -> str:
        """Serialized Student profile for the authenticated student."""
        return f"lms:student_me:{user_id}"

    @staticmethod
    def student_enrollments(student_id: int) -> str:
        return f"lms:student:{student_id}:enrollments"

    @staticmethod
    def student_assignments(student_id: int) -> str:
        return f"lms:student:{student_id}:assignments"

    @staticmethod
    def student_submissions(student_id: int) -> str:
        return f"lms:student:{student_id}:submissions"

    @staticmethod
    def student_by_programme(programme_id=None, level=None) -> str:
        return f"lms:students:programme:{programme_id}:level:{level}"

    @staticmethod
    def my_enrollments(student_id: int) -> str:
        """Core/elective split for the /enrollments/my_enrollments/ action."""
        return f"lms:student:{student_id}:my_enrollments"

    # ── Teacher ───────────────────────────────────────────────────────────────

    @staticmethod
    def teacher_me(user_id: int) -> str:
        return f"lms:teacher_me:{user_id}"

    @staticmethod
    def teacher_courses(teacher_id: int) -> str:
        return f"lms:teacher:{teacher_id}:courses"

    @staticmethod
    def teacher_assignments(teacher_id: int) -> str:
        return f"lms:teacher:{teacher_id}:assignments"

    @staticmethod
    def teacher_students(teacher_id: int) -> str:
        return f"lms:teacher:{teacher_id}:students"

    @staticmethod
    def teacher_by_dept(department=None) -> str:
        return f"lms:teachers:dept:{department}"

    # ── Principal ─────────────────────────────────────────────────────────────

    @staticmethod
    def principal_dashboard() -> str:
        """School-wide aggregate stats shown on the principal dashboard."""
        return "lms:principal:dashboard"

    # ── CourseOffering ────────────────────────────────────────────────────────

    @staticmethod
    def offering_enrollments(offering_id: int) -> str:
        return f"lms:offering:{offering_id}:enrollments"

    @staticmethod
    def offering_assignments(offering_id: int) -> str:
        return f"lms:offering:{offering_id}:assignments"

    @staticmethod
    def offering_quizzes(offering_id: int) -> str:
        return f"lms:offering:{offering_id}:quizzes"


# ==================== INVALIDATION HELPERS ====================
# Each helper deletes the full set of keys that become stale when the
# named entity changes.  Callers (viewset perform_create / perform_update /
# perform_destroy) import exactly the helpers they need.

def invalidate_student_cache(student) -> None:
    """
    Wipe all cached data that is specific to one student.

    Call whenever a student record, enrollment, grade, or submission changes.
    Also clears the principal dashboard because it aggregates student counts.
    """
    cache.delete_many([
        CacheKeys.student_me(student.user_id),
        CacheKeys.student_enrollments(student.id),
        CacheKeys.student_assignments(student.id),
        CacheKeys.student_submissions(student.id),
        CacheKeys.my_enrollments(student.id),
        CacheKeys.student_by_programme(student.programme_id, student.level),
        CacheKeys.principal_dashboard(),
    ])


def invalidate_teacher_cache(teacher) -> None:
    """
    Wipe all cached data that is specific to one teacher.

    Call whenever a teacher record or their course assignments change.
    """
    cache.delete_many([
        CacheKeys.teacher_me(teacher.user_id),
        CacheKeys.teacher_courses(teacher.id),
        CacheKeys.teacher_assignments(teacher.id),
        CacheKeys.teacher_students(teacher.id),
    ])


def invalidate_offering_cache(offering_id: int) -> None:
    """
    Wipe all cached data scoped to a single CourseOffering.

    Also clears the principal dashboard because it counts active
    assignments and quizzes per offering.
    """
    cache.delete_many([
        CacheKeys.offering_enrollments(offering_id),
        CacheKeys.offering_assignments(offering_id),
        CacheKeys.offering_quizzes(offering_id),
        CacheKeys.principal_dashboard(),
    ])


def invalidate_programme_cache(pk) -> None:
    """
    Wipe all cached data related to a Programme.

    Called on programme create / update / delete.
    """
    cache.delete_many([
        CacheKeys.programme_list(),
        CacheKeys.programme_detail(pk),
        CacheKeys.programme_students(pk),
        CacheKeys.programme_electives(pk),      # unfiltered variant
        CacheKeys.principal_dashboard(),
    ])


def invalidate_course_cache(course_pk, offering_id: int = None) -> None:
    """
    Wipe cached data for a Course and, optionally, one of its offerings.

    Pass ``offering_id`` when the mutation also affects a specific offering
    (e.g. deactivating an offering invalidates its enrollment/assignment/quiz
    sub-caches in addition to the course-level caches).
    """
    keys = [
        CacheKeys.course_list(),
        CacheKeys.course_detail(course_pk),
        CacheKeys.course_offerings(course_pk),  # unfiltered variant
    ]
    if offering_id is not None:
        keys += [
            CacheKeys.offering_enrollments(offering_id),
            CacheKeys.offering_assignments(offering_id),
            CacheKeys.offering_quizzes(offering_id),
        ]
    cache.delete_many(keys)


def invalidate_assignment_caches(assignment) -> None:
    """
    Wipe caches affected by a create / update / delete on an Assignment.

    Touches:
      • The parent offering's assignment list
      • The authoring teacher's assignment list
      • Every enrolled student's personal assignment cache
    """
    from .models import Enrollment, Student  # local import avoids circular deps

    invalidate_offering_cache(assignment.course_offering_id)
    invalidate_teacher_cache(assignment.teacher)

    student_ids = (
        Enrollment.objects
        .filter(course_offering_id=assignment.course_offering_id, is_active=True)
        .values_list("student_id", flat=True)
    )
    keys = [
        CacheKeys.student_assignments(sid)
        for sid in Student.objects.filter(id__in=student_ids).values_list("id", flat=True)
    ]
    if keys:
        cache.delete_many(keys)


def invalidate_enrollment_caches(enrollment) -> None:
    """
    Wipe caches affected by a create / delete on an Enrollment.

    Touches the student, the offering, and every teacher assigned to
    that offering (their student-list cache becomes stale).
    """
    invalidate_student_cache(enrollment.student)
    invalidate_offering_cache(enrollment.course_offering_id)

    for teacher in enrollment.course_offering.assigned_teachers.all():
        invalidate_teacher_cache(teacher)