from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from django.contrib.auth import authenticate
from django.core.cache import cache
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from .models import (
    User, Student, Teacher, Principal, Admin,
    Programme, Course, CourseOffering, AcademicTerm,
    Enrollment, Assignment, Submission, Quiz, StudentAnswer,
    QuizAttempt, Question, CourseOutline, CourseResource
)
from .serializers import (
    UserSerializer, StudentSerializer, TeacherSerializer,
    PrincipalSerializer, ProgrammeSerializer, CourseSerializer,
    CourseOfferingSerializer, AcademicTermSerializer, EnrollmentSerializer,
    AssignmentSerializer, SubmissionSerializer, QuizSerializer, ChoiceSerializer,
    StudentAnswerSerializer, ShortAnswerKeySerializer, QuestionSerializer,
    QuizAttemptSerializer, CourseResourceSerializer, CourseOutlineSerializer
)
from .permissions import (
    IsTeacher, IsStudent, IsAdmin, IsTeacherOrAdmin, IsTeacherOfCourse, IsOwnerOrAdmin
)
from .cache import (
    CACHE_TTL,
    CacheKeys,
    invalidate_student_cache,
    invalidate_teacher_cache,
    invalidate_offering_cache,
    invalidate_programme_cache,
    invalidate_course_cache,
    invalidate_assignment_caches,
    invalidate_enrollment_caches,
    invalidate_submission_caches,
    invalidate_attempt_caches,
    invalidate_quiz_caches
)


def get_current_term():
    """
    Return the active AcademicTerm, caching the result to avoid repeated
    DB hits.  ``False`` is stored as a sentinel when no term exists so that
    a cache miss (``None``) is distinguishable from "no term configured".
    """
    cached = cache.get(CacheKeys.current_term())
    if cached is not None:
        return cached  # False means no term; any other value is the term object

    try:
        term = AcademicTerm.objects.get(is_current=True)
    except AcademicTerm.DoesNotExist:
        term = None

    cache.set(
        CacheKeys.current_term(),
        term if term is not None else False,
        CACHE_TTL["current_term"],
    )
    return term


def check_user_role(user, expected_role: str) -> None:
    """Raise 403 when the user does not carry the expected role attribute."""
    if not hasattr(user, expected_role):
        raise PermissionDenied(f"User is not a {expected_role}")


def get_enrolled_course_offerings(student, term=None):
    """Return a queryset of course-offering IDs the student is enrolled in."""
    if term is None:
        term = get_current_term()
    if not term:
        return []
    return Enrollment.objects.filter(
        student=student,
        course_offering__term=term.term_number,
        is_active=True,
    ).values_list("course_offering_id", flat=True)

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdmin()]
        if self.action == "login":
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        role      = request.data.get("role")
        school_id = request.data.get("school_id")
        password  = request.data.get("password")

        if not all([role, school_id, password]):
            return Response(
                {"error": "role, school_id, and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = CacheKeys.login(role, school_id)
        user_data = cache.get(cache_key)

        if not user_data:
            try:
                user = User.objects.get(school_id=school_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not authenticate(request, username=school_id, password=password):
                return Response(
                    {"error": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if user.role != role:
                return Response(
                    {"error": f"User is not a {role}"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            refresh = RefreshToken.for_user(user)
            refresh["user_id"] = user.id
            refresh["role"]    = role

            user_data = {
                "user_id":       user.id,
                "access_token":  str(refresh.access_token),
                "refresh_token": str(refresh),
            }
            cache.set(cache_key, user_data, CACHE_TTL["login"])

        return Response({"message": "Login successful", **user_data},
                        status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def me(self, request):
        cache_key = CacheKeys.user_me(request.user.id)
        user_data = cache.get(cache_key)

        if not user_data:
            user_data = UserSerializer(request.user).data
            cache.set(cache_key, user_data, CACHE_TTL["user_me"])

        return Response({"user": user_data})

    @action(detail=False, methods=["post"])
    def logout(self, request):
        user = request.user
        role_map = {
            "student":   lambda u: (u.student.student_number,    "student"),
            "teacher":   lambda u: (u.teacher.employee_number,   "teacher"),
            "principal": lambda u: (u.principal.employee_number, "principal"),
            "admin":     lambda u: (u.admin.employee_number,     "admin"),
        }
        for role_attr, get_data in role_map.items():
            if hasattr(user, role_attr):
                identifier, role = get_data(user)
                cache.delete(CacheKeys.login(role, identifier))
                break

        cache.delete(CacheKeys.user_me(user.id))
        return Response({"message": "Logged out successfully"})

class ProfileViewSetMixin:
    """Shared helpers for profile-type viewsets."""

    def get_queryset_for_profile(self, model_class, user_attr, related_fields):
        user     = self.request.user
        queryset = model_class.objects.select_related(*related_fields)
        if user.is_staff or user.is_superuser:
            return queryset.all()
        if hasattr(user, user_attr):
            return queryset.filter(user=user)
        return queryset.none()

    def get_me_action(self, user_attr, error_message):
        check_user_role(self.request.user, user_attr)
        instance   = getattr(self.request.user, user_attr)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class StudentViewSet(ProfileViewSetMixin, ModelViewSet):
    queryset           = Student.objects.select_related("user", "programme").all()
    serializer_class   = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        if self.action == "me":
            return [IsAuthenticated(), IsStudent()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user     = self.request.user
        queryset = Student.objects.select_related("user", "programme")

        if user.is_staff or user.is_superuser:
            return queryset.all()
        if hasattr(user, "student"):
            return queryset.filter(user=user)
        if hasattr(user, "teacher"):
            student_ids = Enrollment.objects.filter(
                course_offering__in=user.teacher.assigned_course.all(),
                is_active=True,
            ).values_list("student_id", flat=True).distinct()
            return queryset.filter(id__in=student_ids)
        return queryset.none()

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_student_cache(instance)

    def perform_destroy(self, instance):
        invalidate_student_cache(instance)
        instance.delete()

    @action(detail=False, methods=["get"])
    def me(self, request):
        cache_key = CacheKeys.student_me(request.user.id)
        cached    = cache.get(cache_key)

        if cached is None:
            check_user_role(request.user, "student")
            cached = self.get_serializer(request.user.student).data
            cache.set(cache_key, cached, CACHE_TTL["student_me"])

        return Response(cached)

    def _check_student_access(self, student):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return True
        if hasattr(user, "student") and user.student == student:
            return True
        if hasattr(user, "teacher") and student.enrollments.filter(
            course_offering__in=user.teacher.assigned_course.all(),
            is_active=True,
        ).exists():
            return True
        raise PermissionDenied("You do not have access to this student")

    @action(detail=True, methods=["get"])
    def enrollments(self, request, pk=None):
        student   = self.get_object()
        self._check_student_access(student)
        cache_key = CacheKeys.student_enrollments(student.id)
        data      = cache.get(cache_key)

        if data is None:
            qs   = Enrollment.objects.filter(
                student=student, is_active=True
            ).select_related("course_offering__course")
            data = {
                "student":           student.student_number,
                "student_name":      student.user.get_full_name(),
                "total_enrollments": qs.count(),
                "enrollments":       EnrollmentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["student_enrollments"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        student   = self.get_object()
        self._check_student_access(student)
        cache_key = CacheKeys.student_assignments(student.id)
        data      = cache.get(cache_key)

        if data is None:
            current_term = get_current_term()
            if not current_term:
                return Response(
                    {"error": "No current academic term set"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            enrolled = get_enrolled_course_offerings(student, current_term)
            qs = Assignment.objects.filter(
                course_offering_id__in=enrolled,
                status=Assignment.StatusChoices.PUBLISHED,
            ).select_related("course_offering__course")
            data = {
                "student":           student.student_number,
                "total_assignments": qs.count(),
                "assignments":       AssignmentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["student_assignments"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def submissions(self, request, pk=None):
        student   = self.get_object()
        self._check_student_access(student)
        cache_key = CacheKeys.student_submissions(student.id)
        data      = cache.get(cache_key)

        if data is None:
            qs = Submission.objects.filter(
                student=student
            ).select_related("assignment__course_offering__course")
            data = {
                "student":            student.student_number,
                "total_submissions":  qs.count(),
                "graded_submissions": qs.filter(is_graded=True).count(),
                "submissions":        SubmissionSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["student_submissions"])

        return Response(data)

    @action(detail=False, methods=["get"])
    def by_programme(self, request):
        programme_id = request.query_params.get("programme")
        level        = request.query_params.get("level")
        cache_key    = CacheKeys.student_by_programme(programme_id, level)
        data         = cache.get(cache_key)

        if data is None:
            qs = self.get_queryset()
            if programme_id:
                qs = qs.filter(programme_id=programme_id)
            if level:
                qs = qs.filter(level=int(level))
            data = {
                "total_students": qs.count(),
                "students":       self.get_serializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["student_by_programme"])

        return Response(data)

class TeacherViewSet(ProfileViewSetMixin, ModelViewSet):
    queryset = (
        Teacher.objects
        .select_related("user")
        .prefetch_related("assigned_course")
        .all()
    )
    serializer_class   = TeacherSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        if self.action == "me":
            return [IsAuthenticated(), IsTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user     = self.request.user
        queryset = Teacher.objects.select_related("user").prefetch_related("assigned_course")

        if user.is_staff or user.is_superuser:
            return queryset.all()
        if hasattr(user, "teacher"):
            return queryset.filter(user=user)
        if hasattr(user, "student"):
            offering_ids = Enrollment.objects.filter(
                student=user.student, is_active=True
            ).values_list("course_offering_id", flat=True)
            teacher_ids = (
                Teacher.assigned_course.through.objects
                .filter(courseoffering_id__in=offering_ids)
                .values_list("teacher_id", flat=True)
                .distinct()
            )
            return queryset.filter(id__in=teacher_ids)
        return queryset.none()

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_teacher_cache(instance)

    def perform_destroy(self, instance):
        invalidate_teacher_cache(instance)
        instance.delete()

    @action(detail=False, methods=["get"])
    def me(self, request):
        cache_key = CacheKeys.teacher_me(request.user.id)
        cached    = cache.get(cache_key)

        if cached is None:
            check_user_role(request.user, "teacher")
            cached = self.get_serializer(request.user.teacher).data
            cache.set(cache_key, cached, CACHE_TTL["teacher_me"])

        return Response(cached)

    @action(detail=True, methods=["get"])
    def courses(self, request, pk=None):
        teacher   = self.get_object()
        cache_key = CacheKeys.teacher_courses(teacher.id)
        data      = cache.get(cache_key)

        if data is None:
            qs   = teacher.assigned_course.select_related("course").all()
            data = {
                "teacher":         teacher.user.get_full_name(),
                "employee_number": teacher.employee_number,
                "total_courses":   qs.count(),
                "courses":         CourseOfferingSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["teacher_courses"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        teacher   = self.get_object()
        cache_key = CacheKeys.teacher_assignments(teacher.id)
        data      = cache.get(cache_key)

        if data is None:
            qs   = Assignment.objects.filter(
                teacher=teacher
            ).select_related("course_offering__course")
            data = {
                "teacher":           teacher.user.get_full_name(),
                "total_assignments": qs.count(),
                "assignments":       AssignmentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["teacher_assignments"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        teacher   = self.get_object()
        cache_key = CacheKeys.teacher_students(teacher.id)
        data      = cache.get(cache_key)

        if data is None:
            student_ids = Enrollment.objects.filter(
                course_offering__in=teacher.assigned_course.all(),
                is_active=True,
            ).values_list("student_id", flat=True).distinct()
            qs = Student.objects.filter(
                id__in=student_ids
            ).select_related("user", "programme")
            data = {
                "teacher":        teacher.user.get_full_name(),
                "total_students": qs.count(),
                "students":       StudentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["teacher_students"])

        return Response(data)

    @action(detail=False, methods=["get"])
    def by_department(self, request):
        department = request.query_params.get("department")
        cache_key  = CacheKeys.teacher_by_dept(department)
        data       = cache.get(cache_key)

        if data is None:
            qs = self.get_queryset()
            if department:
                qs = qs.filter(department__icontains=department)
            data = {
                "total_teachers": qs.count(),
                "teachers":       self.get_serializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["teacher_by_dept"])

        return Response(data)

class PrincipalViewSet(ProfileViewSetMixin, ModelViewSet):
    queryset           = Principal.objects.select_related("user").all()
    serializer_class   = PrincipalSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return self.get_queryset_for_profile(Principal, "principal", ["user"])

    @action(detail=False, methods=["get"])
    def me(self, request):
        return self.get_me_action("principal", "User is not a principal")

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        check_user_role(request.user, "principal")
        cache_key = CacheKeys.principal_dashboard()
        data      = cache.get(cache_key)

        if data is None:
            current_term = get_current_term()
            data = {
                "total_students":     Student.objects.count(),
                "total_teachers":     Teacher.objects.count(),
                "total_programmes":   Programme.objects.count(),
                "active_assignments": 0,
                "active_quizzes":     0,
            }
            if current_term:
                data["active_assignments"] = Assignment.objects.filter(
                    status=Assignment.StatusChoices.PUBLISHED,
                    course_offering__term=current_term.term_number,
                ).count()
                data["active_quizzes"] = Quiz.objects.filter(
                    status=Quiz.StatusChoices.PUBLISHED,
                    course_offering__term=current_term.term_number,
                ).count()
            cache.set(cache_key, data, CACHE_TTL["principal_dashboard"])

        return Response(data)

class ProgrammeViewSet(ModelViewSet):
    queryset           = Programme.objects.all()
    serializer_class   = ProgrammeSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()
        cache.delete_many([
            CacheKeys.programme_list(),
            CacheKeys.principal_dashboard(),
        ])

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_programme_cache(instance.pk)

    def perform_destroy(self, instance):
        invalidate_programme_cache(instance.pk)
        instance.delete()
        
    def list(self, request, *args, **kwargs):
        cache_key = CacheKeys.programme_list()
        data      = cache.get(cache_key)
        if data is None:
            data = super().list(request, *args, **kwargs).data
            cache.set(cache_key, data, CACHE_TTL["programme_list"])
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        cache_key = CacheKeys.programme_detail(kwargs["pk"])
        data      = cache.get(cache_key)
        if data is None:
            data = super().retrieve(request, *args, **kwargs).data
            cache.set(cache_key, data, CACHE_TTL["programme_detail"])
        return Response(data)

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        programme = self.get_object()
        cache_key = CacheKeys.programme_students(pk)
        data      = cache.get(cache_key)

        if data is None:
            qs   = programme.students.select_related("user").all()
            data = {
                "programme":      programme.name,
                "total_students": qs.count(),
                "students":       StudentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["programme_students"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def electives(self, request, pk=None):
        programme = self.get_object()
        level     = request.query_params.get("level")
        term      = request.query_params.get("term")
        cache_key = CacheKeys.programme_electives(pk, level, term)
        data      = cache.get(cache_key)

        if data is None:
            electives = programme.elective_courses.all()

            if level and term:
                current_term = get_current_term()
                if not current_term:
                    return Response(
                        {"error": "No current academic term set"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                offerings = CourseOffering.objects.filter(
                    course__in=electives,
                    level=int(level),
                    term=int(term),
                    is_active=True,
                ).select_related("course")
                data = {
                    "programme":           programme.name,
                    "level":               int(level),
                    "term":                int(term),
                    "available_electives": CourseOfferingSerializer(offerings, many=True).data,
                }
            else:
                data = {
                    "programme":      programme.name,
                    "total_electives": electives.count(),
                    "electives":       CourseSerializer(electives, many=True).data,
                }
            cache.set(cache_key, data, CACHE_TTL["programme_electives"])

        return Response(data)

class CourseViewSet(ModelViewSet):
    queryset           = Course.objects.prefetch_related("programmes").all()
    serializer_class   = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset     = Course.objects.prefetch_related("programmes")
        course_type  = self.request.query_params.get("course_type")
        programme_id = self.request.query_params.get("programme")
        if course_type:
            queryset = queryset.filter(course_type=course_type.upper())
        if programme_id:
            queryset = queryset.filter(programmes__id=programme_id)
        return queryset.distinct()

    def perform_create(self, serializer):
        serializer.save()
        cache.delete_many([
            CacheKeys.course_list(),
            CacheKeys.programme_list(),
        ])

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_course_cache(instance.pk)

    def perform_destroy(self, instance):
        invalidate_course_cache(instance.pk)
        instance.delete()

    def list(self, request, *args, **kwargs):
        course_type  = request.query_params.get("course_type")
        programme_id = request.query_params.get("programme")
        cache_key    = CacheKeys.course_list(course_type, programme_id)
        data         = cache.get(cache_key)
        if data is None:
            data = super().list(request, *args, **kwargs).data
            cache.set(cache_key, data, CACHE_TTL["course_list"])
        return Response(data)

    def retrieve(self, request, *args, **kwargs):
        cache_key = CacheKeys.course_detail(kwargs["pk"])
        data      = cache.get(cache_key)
        if data is None:
            data = super().retrieve(request, *args, **kwargs).data
            cache.set(cache_key, data, CACHE_TTL["course_detail"])
        return Response(data)

    @action(detail=True, methods=["get"])
    def offerings(self, request, pk=None):
        course    = self.get_object()
        level     = request.query_params.get("level")
        term      = request.query_params.get("term")
        cache_key = CacheKeys.course_offerings(pk, level, term)
        data      = cache.get(cache_key)

        if data is None:
            qs = CourseOffering.objects.filter(course=course, is_active=True)
            if level:
                qs = qs.filter(level=int(level))
            if term:
                qs = qs.filter(term=int(term))
            data = {
                "course":          course.name,
                "course_code":     course.code_prefix,
                "total_offerings": qs.count(),
                "offerings":       CourseOfferingSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["course_offerings"])

        return Response(data)

class CourseOfferingViewSet(ModelViewSet):
    queryset           = CourseOffering.objects.select_related("course").all()
    serializer_class   = CourseOfferingSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = CourseOffering.objects.select_related("course")
        user     = self.request.user

        filters = {}
        for param in ["level", "term", "course_type", "programme"]:
            value = self.request.query_params.get(param)
            if value:
                if param == "course_type":
                    filters["course__course_type"] = value.upper()
                elif param == "programme":
                    filters["course__programmes__id"] = value
                else:
                    filters[param] = int(value)

        queryset = queryset.filter(**filters)

        if hasattr(user, "student"):
            current_term = get_current_term()
            if current_term:
                queryset = queryset.filter(
                    term=current_term.term_number, is_active=True
                )
        elif hasattr(user, "teacher") and not filters:
            queryset = queryset.filter(
                id__in=user.teacher.assigned_course.values_list("id", flat=True)
            )

        return queryset.distinct()

    def perform_update(self, serializer):
        instance = serializer.save()
        invalidate_offering_cache(instance.id)
        invalidate_course_cache(instance.course_id, instance.id)

    def perform_destroy(self, instance):
        invalidate_offering_cache(instance.id)
        invalidate_course_cache(instance.course_id, instance.id)
        instance.delete()

    def _check_teaching_access(self, offering):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return True
        if hasattr(self.request.user, "teacher") and (
            self.request.user.teacher.assigned_course.filter(id=offering.id).exists()
        ):
            return True
        raise PermissionDenied("Only teachers and admins can view enrollments")

    @action(detail=True, methods=["get"])
    def enrollments(self, request, pk=None):
        offering  = self.get_object()
        self._check_teaching_access(offering)
        cache_key = CacheKeys.offering_enrollments(offering.id)
        data      = cache.get(cache_key)

        if data is None:
            qs   = Enrollment.objects.filter(
                course_offering=offering, is_active=True
            ).select_related("student__user")
            data = {
                "course_code":    offering.course_code,
                "course_name":    offering.course.name,
                "level":          offering.level,
                "term":           offering.term,
                "total_enrolled": qs.count(),
                "enrollments":    EnrollmentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["offering_enrollments"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        offering  = self.get_object()
        cache_key = CacheKeys.offering_assignments(offering.id)
        data      = cache.get(cache_key)

        if data is None:
            qs = Assignment.objects.filter(
                course_offering=offering
            ).select_related("teacher__user")
            if hasattr(request.user, "student"):
                qs = qs.filter(status=Assignment.StatusChoices.PUBLISHED)
            data = {
                "course_code":       offering.course_code,
                "course_name":       offering.course.name,
                "total_assignments": qs.count(),
                "assignments":       AssignmentSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["offering_assignments"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def quizzes(self, request, pk=None):
        offering  = self.get_object()
        cache_key = CacheKeys.offering_quizzes(offering.id)
        data      = cache.get(cache_key)

        if data is None:
            qs = Quiz.objects.filter(
                course_offering=offering
            ).select_related("teacher__user")
            if hasattr(request.user, "student"):
                qs = qs.filter(status=Quiz.StatusChoices.PUBLISHED)
            data = {
                "course_code":   offering.course_code,
                "course_name":   offering.course.name,
                "total_quizzes": qs.count(),
                "quizzes":       QuizSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["offering_quizzes"])

        return Response(data)


    @action(detail=True, methods=["get"])
    def outline(self, request, pk=None):
        offering = self.get_object()
        cache_key = f"offering_{offering.id}_outline"
        data = cache.get(cache_key)

        if data is None:
            print('not from cache')
            qs = CourseOutline.objects.filter(course_offering=offering).order_by("week")
            data = {
                "course_code": offering.course_code,
                "course_name": offering.course.name,
                "total_weeks": qs.count(),
                "progress": offering.progress,
                "weeks": CourseOutlineSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL.get("offering_weeks", 300))
            print('set to cache')

        return Response(data)


    @action(detail=True, methods=["get"])
    def resources(self, request, pk=None):
        offering  = self.get_object()
        cache_key = f"offering_{offering.id}_resources"
        data      = cache.get(cache_key)

        if data is None:
            qs   = CourseResource.objects.filter(course_offering=offering).order_by("-uploaded_at")
            data = {
                "course_code":    offering.course_code,
                "course_name":    offering.course.name,
                "total_resources": qs.count(),
                "resources":      CourseResourceSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL.get("offering_resources", 300))

        return Response(data)


    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        offering = self.get_object()
        cache_key = f"offering_{offering.id}_stats"
        data      = cache.get(cache_key)

        if data is None:
            assignments_qs = Assignment.objects.filter(
                course_offering=offering,
                status=Assignment.StatusChoices.PUBLISHED
            )
            quizzes_qs = Quiz.objects.filter(
                course_offering=offering,
                status=Quiz.StatusChoices.PUBLISHED
            )

            grade = None
            if hasattr(request.user, "student"):
                enrollment = Enrollment.objects.filter(
                    student=request.user.student,
                    course_offering=offering
                ).first()
                grade = enrollment.grade if enrollment else None

            data = {
                "course_code": offering.course_code,
                "progress":    offering.progress,
                "grade":       grade or "N/A",
                "assignments": assignments_qs.count(),
                "quizzes":     quizzes_qs.count(),
            }
            cache.set(cache_key, data, CACHE_TTL.get("offering_stats", 300))

        return Response(data)
    
class EnrollmentViewSet(ModelViewSet):
    queryset = Enrollment.objects.select_related(
        "student__user", "course_offering__course"
    ).all()
    serializer_class = EnrollmentSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy", "bulk_enroll"]:
            return [IsAuthenticated(), IsAdmin()]
        if self.action in ["update", "partial_update", "update_grade"]:
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user     = self.request.user
        queryset = Enrollment.objects.select_related(
            "student__user", "course_offering__course"
        )
        if user.is_staff or user.is_superuser:
            return queryset.all()
        if hasattr(user, "student"):
            current_term = get_current_term()
            if current_term:
                return queryset.filter(
                    student=user.student,
                    course_offering__term=current_term.term_number,
                    is_active=True,
                )
            return queryset.filter(student=user.student, is_active=True)
        if hasattr(user, "teacher"):
            return queryset.filter(
                course_offering__in=user.teacher.assigned_course.all()
            )
        return queryset.none()

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        if self.action in ["update", "partial_update"]:
            if request.user.is_staff or request.user.is_superuser:
                return
            if hasattr(request.user, "teacher"):
                is_teaching = request.user.teacher.assigned_course.filter(
                    id=obj.course_offering.id
                ).exists()
                if is_teaching:
                    if not set(request.data.keys()).issubset({"grade"}):
                        raise PermissionDenied("Teachers can only update the grade field.")
                    return
                raise PermissionDenied("You are not teaching this course.")
            raise PermissionDenied("You don't have permission to modify enrollments.")


    def perform_create(self, serializer):
        enrollment = serializer.save()
        invalidate_enrollment_caches(enrollment)

    def perform_destroy(self, instance):
        invalidate_enrollment_caches(instance)
        instance.delete()


    @action(detail=False, methods=["get"])
    def my_enrollments(self, request):
        check_user_role(request.user, "student")
        student   = request.user.student
        cache_key = CacheKeys.my_enrollments(student.id)
        data      = cache.get(cache_key)

        if data is None:
            current_term = get_current_term()
            if not current_term:
                return Response(
                    {"error": "No current academic term set"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            qs = Enrollment.objects.filter(
                student=student,
                course_offering__term=current_term.term_number,
                is_active=True,
            ).select_related("course_offering__course")

            serialized = self.get_serializer(qs, many=True).data
            data = {
                "term":             current_term.term_number,
                "academic_year":    current_term.academic_year,
                "core_courses":     [e for e in serialized if e["is_core"]],
                "elective_courses": [e for e in serialized if not e["is_core"]],
                "total_courses":    len(serialized),
            }
            cache.set(cache_key, data, CACHE_TTL["my_enrollments"])

        return Response(data)

    @action(detail=False, methods=["post"])
    def bulk_enroll(self, request):
        student_ids        = request.data.get("student_ids", [])
        course_offering_id = request.data.get("course_offering_id")
        is_core            = request.data.get("is_core", False)

        if not student_ids or not course_offering_id:
            return Response(
                {"error": "student_ids and course_offering_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            course_offering = CourseOffering.objects.get(id=course_offering_id)
            students        = Student.objects.filter(id__in=student_ids)

            if students.count() != len(student_ids):
                return Response(
                    {"error": "Some student IDs are invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            created_enrollments = []
            for student in students:
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    course_offering=course_offering,
                    defaults={"is_core": is_core},
                )
                if created:
                    created_enrollments.append(enrollment)
                    invalidate_student_cache(student)

            # Invalidate offering-level caches once after the loop
            invalidate_offering_cache(course_offering_id)

            return Response(
                {
                    "message":        f"Successfully enrolled {len(created_enrollments)} students",
                    "enrolled_count": len(created_enrollments),
                },
                status=status.HTTP_201_CREATED,
            )
        except CourseOffering.DoesNotExist:
            return Response(
                {"error": "Course offering not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"])
    def update_grade(self, request, pk=None):
        enrollment = self.get_object()
        grade      = request.data.get("grade")

        if not grade:
            return Response(
                {"error": "Grade is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not (request.user.is_staff or request.user.is_superuser):
            if hasattr(request.user, "teacher"):
                is_teaching = request.user.teacher.assigned_course.filter(
                    id=enrollment.course_offering.id
                ).exists()
                if not is_teaching:
                    return Response(
                        {"error": "You are not teaching this course"},
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                return Response(
                    {"error": "Only teachers and admins can update grades"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        enrollment.grade = grade
        enrollment.save(update_fields=["grade"])

        invalidate_student_cache(enrollment.student)
        invalidate_offering_cache(enrollment.course_offering_id)

        return Response(self.get_serializer(enrollment).data)


class AssignmentViewSet(ModelViewSet):
    queryset = Assignment.objects.select_related(
        "course_offering__course", "teacher__user"
    ).all()
    serializer_class = AssignmentSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsTeacher()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), (IsTeacherOfCourse | IsAdmin)]
        return [IsAuthenticated()]

    def get_queryset(self):
        user     = self.request.user
        queryset = Assignment.objects.select_related(
            "course_offering__course", "teacher__user"
        )
        if user.is_staff or user.is_superuser:
            return queryset.all()
        if hasattr(user, "teacher"):
            return queryset.filter(teacher=user.teacher)
        if hasattr(user, "student"):
            current_term = get_current_term()
            if not current_term:
                return queryset.none()
            enrolled = get_enrolled_course_offerings(user.student, current_term)
            return queryset.filter(
                course_offering_id__in=enrolled,
                status=Assignment.StatusChoices.PUBLISHED,
            )
        return queryset.none()

    def perform_create(self, serializer):
        assignment = serializer.save(teacher=self.request.user.teacher)
        invalidate_assignment_caches(assignment)

    def perform_update(self, serializer):
        assignment = serializer.save()
        invalidate_assignment_caches(assignment)

    def perform_destroy(self, instance):
        invalidate_assignment_caches(instance)
        instance.delete()


class SubmissionViewSet(ModelViewSet):
    queryset = Submission.objects.select_related(
        "assignment__course_offering__course", "student__user"
    ).all()
    serializer_class = SubmissionSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsStudent()]
        if self.action in ["update", "partial_update"]:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        if self.action == "destroy":
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user     = self.request.user
        queryset = Submission.objects.select_related(
            "assignment__course_offering__course", "student__user"
        )
        if user.is_staff or user.is_superuser:
            return queryset.all()
        if hasattr(user, "student"):
            return queryset.filter(student=user.student)
        if hasattr(user, "teacher"):
            return queryset.filter(
                assignment__teacher=user.teacher
            )
        return queryset.none()

    def perform_create(self, serializer):
        submission = serializer.save(student=self.request.user.student)
        invalidate_submission_caches(submission)

    def perform_update(self, serializer):
        submission = serializer.save()
        invalidate_submission_caches(submission)

    def perform_destroy(self, instance):
        invalidate_submission_caches(instance)
        instance.delete()


class QuizViewSet(ModelViewSet):
    """
    CRUD for quizzes plus teacher and student-specific actions.

    Role behaviour
    --------------
    Teacher  – sees only the quizzes they authored; can create, edit, delete,
               publish/close, and view all attempts.
    Student  – sees only PUBLISHED quizzes in their current-term enrolled
               offerings; can start an attempt via /quizzes/{id}/start/.
    Admin    – full access to everything.
    """

    queryset = Quiz.objects.select_related(
        "course_offering__course",
        "teacher__user",
    ).prefetch_related("questions__choices", "questions__answer_keys").all()
    serializer_class = QuizSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsTeacher()]
        if self.action in ["update", "partial_update", "destroy",
                            "publish", "close", "attempts"]:
            return [IsAuthenticated(), IsTeacherOfCourse | IsAdmin]
        if self.action == "start":
            return [IsAuthenticated(), IsStudent()]
        return [IsAuthenticated()]

    # ── Queryset scoping ──────────────────────────────────────────────────────

    def get_queryset(self):
        user     = self.request.user
        queryset = Quiz.objects.select_related(
            "course_offering__course",
            "teacher__user",
        ).prefetch_related("questions__choices", "questions__answer_keys")

        if user.is_staff or user.is_superuser:
            return queryset.all()

        if hasattr(user, "teacher"):
            return queryset.filter(teacher=user.teacher)

        if hasattr(user, "student"):
            current_term = get_current_term()
            if not current_term:
                return queryset.none()
            enrolled = get_enrolled_course_offerings(user.student, current_term)
            quizzes = queryset.filter(
                course_offering_id__in=enrolled,
                status=Quiz.StatusChoices.PUBLISHED,
            )
            return quizzes
        return queryset.none()

    # ── Retrieve with caching ─────────────────────────────────────────────────
    @staticmethod
    def _strip_answers(quiz_data: dict) -> dict:
        """
        Remove is_correct from choices and drop answer_keys entirely
        so students cannot see the correct answers before submitting.
        """
        for question in quiz_data.get("questions", []):
            for choice in question.get("choices", []):
                choice.pop("is_correct", None)
            question.pop("answer_keys", None)
        return quiz_data

    def retrieve(self, request, *args, **kwargs):
        quiz      = self.get_object()
        cache_key = CacheKeys.quiz_detail(quiz.id)
        data      = cache.get(cache_key)

        if data is None:
            data = self.get_serializer(quiz).data
            # Strip correct-answer fields when a student is fetching
            if hasattr(request.user, "student"):
                data = self._strip_answers(data)
            cache.set(cache_key, data, CACHE_TTL["quiz_detail"])

        return Response(data)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if hasattr(request.user, "student"):
            response.data = [self._strip_answers(quiz) for quiz in response.data]
        return response

    # ── Write hooks ───────────────────────────────────────────────────────────

    def perform_create(self, serializer):
        quiz = serializer.save(teacher=self.request.user.teacher)
        invalidate_quiz_caches(quiz)

    def perform_update(self, serializer):
        quiz = serializer.save()
        invalidate_quiz_caches(quiz)

    def perform_destroy(self, instance):
        invalidate_quiz_caches(instance)
        instance.delete()

    # ── Private helpers ─────────────────────────────────────────────────

    def _assert_teacher_owns_quiz(self, quiz):
        """Raise 403 if the authenticated teacher did not author this quiz."""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return
        if hasattr(user, "teacher") and quiz.teacher != user.teacher:
            raise PermissionDenied("You did not create this quiz.")

    # ── Actions ───────────────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def questions(self, request, pk=None):
        """
        Return all questions for a quiz.

        Students see questions without correct-answer metadata.
        Teachers and admins see the full question including answer keys.
        """
        quiz      = self.get_object()
        cache_key = CacheKeys.quiz_questions(quiz.id)
        data      = cache.get(cache_key)

        if data is None:
            questions = quiz.questions.prefetch_related(
                "choices", "answer_keys"
            ).order_by("order")
            data = QuestionSerializer(questions, many=True).data
            cache.set(cache_key, data, CACHE_TTL["quiz_questions"])

        if hasattr(request.user, "student"):
            data = [
                {
                    **q,
                    "choices":     [{k: v for k, v in c.items() if k != "is_correct"}
                                    for c in q.get("choices", [])],
                    "answer_keys": [],
                }
                for q in data
            ]

        return Response({
            "quiz_id":        quiz.id,
            "title":          quiz.title,
            "total_questions": len(data),
            "questions":      data,
        })

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """
        Transition a quiz from DRAFT → PUBLISHED.

        Requires at least one question to be present.
        Teacher only (must own the quiz).
        """
        quiz = self.get_object()
        self._assert_teacher_owns_quiz(quiz)

        if quiz.status == Quiz.StatusChoices.PUBLISHED:
            return Response(
                {"error": "Quiz is already published."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not quiz.questions.exists():
            return Response(
                {"error": "Cannot publish a quiz with no questions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quiz.status = Quiz.StatusChoices.PUBLISHED
        quiz.save(update_fields=["status"])
        invalidate_quiz_caches(quiz)

        return Response(
            {"message": f'Quiz "{quiz.title}" is now published.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        """
        Transition a quiz from PUBLISHED → CLOSED.

        Teacher only (must own the quiz).
        """
        quiz = self.get_object()
        self._assert_teacher_owns_quiz(quiz)

        if quiz.status == Quiz.StatusChoices.CLOSED:
            return Response(
                {"error": "Quiz is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quiz.status = Quiz.StatusChoices.CLOSED
        quiz.save(update_fields=["status"])
        invalidate_quiz_caches(quiz)

        return Response(
            {"message": f'Quiz "{quiz.title}" has been closed.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def attempts(self, request, pk=None):
        """
        List all attempts on a quiz.

        Teacher/admin only.  Response is cached per quiz.
        """
        quiz      = self.get_object()
        cache_key = CacheKeys.quiz_attempts(quiz.id)
        data      = cache.get(cache_key)

        if data is None:
            qs = QuizAttempt.objects.filter(
                quiz=quiz
            ).select_related("student__user").order_by("-started_at")
            data = {
                "quiz_id":       quiz.id,
                "title":         quiz.title,
                "total_attempts": qs.count(),
                "attempts":      QuizAttemptSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["quiz_attempts"])

        return Response(data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """
        Start a new attempt on a published quiz.

        Student only.  Enforces:
          - Quiz must be PUBLISHED
          - Quiz must be within its start/end time window (if set)
          - Student must be enrolled in the offering
          - Student must not exceed max_attempts
        """
        quiz    = self.get_object()
        student = request.user.student

        # ── Guard: quiz must be published ─────────────────────────────────────
        if quiz.status != Quiz.StatusChoices.PUBLISHED:
            return Response(
                {"error": "This quiz is not currently available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Guard: time window ────────────────────────────────────────────────
        now = timezone.now()
        if quiz.start_time and now < quiz.start_time:
            return Response(
                {"error": "This quiz has not started yet.",
                 "starts_at": quiz.start_time},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if quiz.end_time and now > quiz.end_time:
            return Response(
                {"error": "This quiz has already ended.",
                 "ended_at": quiz.end_time},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Guard: enrollment check ───────────────────────────────────────────
        enrolled = Enrollment.objects.filter(
            student=student,
            course_offering=quiz.course_offering,
            is_active=True,
        ).exists()
        if not enrolled:
            return Response(
                {"error": "You are not enrolled in the course for this quiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Guard: attempt cap ────────────────────────────────────────────────
        attempt_count = QuizAttempt.objects.filter(
            quiz=quiz, student=student
        ).count()
        if quiz.max_attempts and attempt_count >= quiz.max_attempts:
            return Response(
                {"error": f"You have reached the maximum of "
                           f"{quiz.max_attempts} attempt(s) for this quiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Create attempt ────────────────────────────────────────────────────
        attempt = QuizAttempt.objects.create(
            quiz           = quiz,
            student        = student,
            attempt_number = attempt_count + 1,
            status         = QuizAttempt.StatusChoices.IN_PROGRESS,
            started_at     = now,
        )
        invalidate_attempt_caches(attempt)

        # Return the quiz questions (without answers) so the client can render
        questions = quiz.questions.prefetch_related(
            "choices", "answer_keys"
        ).order_by("order")
        questions_data = [
            {
                **QuestionSerializer(q).data,
                "choices":     [{k: v for k, v in c.items() if k != "is_correct"}
                                for c in QuestionSerializer(q).data.get("choices", [])],
                "answer_keys": [],
            }
            for q in questions
        ]

        return Response(
            {
                "attempt_id":    attempt.id,
                "attempt_number": attempt.attempt_number,
                "quiz_id":       quiz.id,
                "title":         quiz.title,
                "duration_minutes": quiz.duration_minutes,
                "started_at":    attempt.started_at,
                "questions":     questions_data,
            },
            status=status.HTTP_201_CREATED,
        )


# ==================== QUIZ ATTEMPT VIEWSET ====================

class QuizAttemptViewSet(ModelViewSet):
    """
    Manage quiz attempts and answer submission.

    Key actions
    -----------
    submit      – student submits answers and attempt is auto-graded
    my_attempts – student lists their own attempts for a given quiz
    result      – retrieve graded result for a completed attempt
    grade       – teacher manually grades or overrides marks (e.g. short-answer)
    """

    queryset = QuizAttempt.objects.select_related(
        "quiz__course_offering__course",
        "quiz__teacher__user",
        "student__user",
    ).prefetch_related("answers__question", "answers__selected_choice").all()
    serializer_class = QuizAttemptSerializer

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy", "grade"]:
            return [IsAuthenticated(), IsTeacherOrAdmin]
        if self.action in ["submit", "my_attempts"]:
            return [IsAuthenticated(), IsStudent()]
        return [IsAuthenticated()]

    # ── Queryset scoping ──────────────────────────────────────────────────────

    def get_queryset(self):
        user     = self.request.user
        queryset = QuizAttempt.objects.select_related(
            "quiz__course_offering__course",
            "quiz__teacher__user",
            "student__user",
        ).prefetch_related("answers__question", "answers__selected_choice")

        if user.is_staff or user.is_superuser:
            return queryset.all()

        if hasattr(user, "teacher"):
            # Teachers see attempts for quizzes they authored
            return queryset.filter(quiz__teacher=user.teacher)

        if hasattr(user, "student"):
            return queryset.filter(student=user.student)

        return queryset.none()

    # ── Retrieve with caching ─────────────────────────────────────────────────

    def retrieve(self, request, *args, **kwargs):
        attempt   = self.get_object()
        cache_key = CacheKeys.attempt_detail(attempt.id)
        data      = cache.get(cache_key)

        if data is None:
            data = self.get_serializer(attempt).data
            cache.set(cache_key, data, CACHE_TTL["attempt_detail"])

        return Response(data)

    # ── Write hooks ───────────────────────────────────────────────────────────

    def perform_update(self, serializer):
        attempt = serializer.save()
        invalidate_attempt_caches(attempt)

    def perform_destroy(self, instance):
        invalidate_attempt_caches(instance)
        instance.delete()

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _auto_grade(attempt: QuizAttempt) -> None:
        """
        Auto-grade all answerable questions on a submitted attempt.

        MCQ / True-False  → matched against Choice.is_correct
        Short answer      → compared (case-insensitive) against ShortAnswerKey
        Multi-select      → all correct choices must be selected, none wrong
        """
        total_marks    = 0
        marks_obtained = 0

        answers = StudentAnswer.objects.filter(
            attempt=attempt
        ).select_related("question").prefetch_related(
            "selected_choice",
            "selected_choices",
            "question__choices",
            "question__answer_keys",
        )

        for answer in answers:
            question   = answer.question
            q_type     = question.question_type
            max_marks  = question.marks
            total_marks += max_marks
            awarded    = 0

            if q_type in (Question.TypeChoices.MCQ, Question.TypeChoices.TRUE_FALSE):
                if answer.selected_choice and answer.selected_choice.is_correct:
                    awarded = max_marks

            elif q_type == Question.TypeChoices.MULTI_SELECT:
                correct_ids = set(
                    question.choices.filter(is_correct=True).values_list("id", flat=True)
                )
                selected_ids = set(
                    answer.selected_choices.values_list("id", flat=True)
                )
                if selected_ids == correct_ids:
                    awarded = max_marks

            elif q_type == Question.TypeChoices.SHORT_ANSWER:
                accepted = {
                    k.text.strip().lower()
                    for k in question.answer_keys.all()
                }
                if answer.text_answer and answer.text_answer.strip().lower() in accepted:
                    awarded = max_marks
                # else: leave as 0 – teacher can override via /grade/

            answer.marks_awarded = awarded
            answer.is_correct    = awarded > 0

        # Bulk-save all answers in one query
        StudentAnswer.objects.bulk_update(answers, ["marks_awarded", "is_correct"])

        # Update attempt totals
        marks_obtained       = sum(a.marks_awarded for a in answers)
        attempt.marks_obtained = marks_obtained
        attempt.percentage     = (
            (marks_obtained / total_marks * 100) if total_marks else 0
        )
        attempt.status         = QuizAttempt.StatusChoices.SUBMITTED
        attempt.submitted_at   = timezone.now()
        attempt.save(update_fields=[
            "marks_obtained", "percentage", "status", "submitted_at"
        ])

    # ── Actions ───────────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """
        Submit answers for an in-progress attempt and trigger auto-grading.

        Expected request body::

            {
              "answers": [
                {
                  "question":        1,
                  "selected_choice": 3,          // MCQ / T-F
                  "selected_choices": [3, 5],    // multi-select
                  "text_answer":     "osmosis"   // short answer
                },
                ...
              ]
            }

        Returns the graded attempt with per-question marks.
        Student only.  Can only submit an IN_PROGRESS attempt that belongs
        to the authenticated student.
        """
        attempt = self.get_object()
        student = request.user.student

        # ── Guard: ownership ──────────────────────────────────────────────────
        if attempt.student != student:
            raise PermissionDenied("This attempt does not belong to you.")

        # ── Guard: state ──────────────────────────────────────────────────────
        if attempt.status != QuizAttempt.StatusChoices.IN_PROGRESS:
            return Response(
                {"error": "This attempt has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Guard: time limit ─────────────────────────────────────────────────
        if attempt.quiz.duration_minutes:
            elapsed = (timezone.now() - attempt.started_at).total_seconds() / 60
            if elapsed > attempt.quiz.duration_minutes + 1:  # 1-min grace period
                return Response(
                    {"error": "Time limit exceeded. Your attempt has expired."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        answers_data = request.data.get("answers", [])
        if not answers_data:
            return Response(
                {"error": "No answers provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_question_ids = set(
            attempt.quiz.questions.values_list("id", flat=True)
        )

        with transaction.atomic():
            # Delete any pre-existing answers (allow resubmit within session)
            StudentAnswer.objects.filter(attempt=attempt).delete()

            for item in answers_data:
                question_id = item.get("question")
                if question_id not in valid_question_ids:
                    raise ValidationError(
                        f"Question {question_id} does not belong to this quiz."
                    )

                answer = StudentAnswer.objects.create(
                    attempt          = attempt,
                    question_id      = question_id,
                    selected_choice_id = item.get("selected_choice"),
                    text_answer      = item.get("text_answer", ""),
                )
                # Many-to-many for multi-select
                multi = item.get("selected_choices", [])
                if multi:
                    answer.selected_choices.set(multi)

            self._auto_grade(attempt)

        invalidate_attempt_caches(attempt)
        invalidate_offering_cache(attempt.quiz.course_offering_id)

        return Response(
            QuizAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def my_attempts(self, request):
        """
        List the authenticated student's own attempts, optionally filtered
        to a single quiz.

        Query params
        ------------
        quiz : int  – Quiz ID to filter by (optional)
        """
        check_user_role(request.user, "student")
        student  = request.user.student
        quiz_id  = request.query_params.get("quiz")

        cache_key = CacheKeys.my_attempts(student.id, quiz_id or "all")
        data      = cache.get(cache_key)

        if data is None:
            qs = QuizAttempt.objects.filter(
                student=student
            ).select_related("quiz").order_by("-started_at")
            if quiz_id:
                qs = qs.filter(quiz_id=quiz_id)

            data = {
                "student":        student.student_number,
                "total_attempts": qs.count(),
                "attempts":       QuizAttemptSerializer(qs, many=True).data,
            }
            cache.set(cache_key, data, CACHE_TTL["my_attempts"])

        return Response(data)

    @action(detail=True, methods=["get"])
    def result(self, request, pk=None):
        """
        Retrieve the graded result for a completed attempt.

        Students may only view their own results.
        Response is cached with a longer TTL since results are stable.
        """
        attempt = self.get_object()

        # Students restricted to their own results
        if hasattr(request.user, "student") and attempt.student != request.user.student:
            raise PermissionDenied("You can only view your own results.")

        if attempt.status not in (
            QuizAttempt.StatusChoices.SUBMITTED,
            QuizAttempt.StatusChoices.GRADED,
        ):
            return Response(
                {"error": "This attempt has not been submitted yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = CacheKeys.attempt_result(attempt.id)
        data      = cache.get(cache_key)

        if data is None:
            serialized = QuizAttemptSerializer(attempt).data
            data = {
                **serialized,
                "quiz_title":    attempt.quiz.title,
                "total_marks":   attempt.quiz.total_marks,
                "passed":        attempt.percentage >= 50,
            }
            cache.set(cache_key, data, CACHE_TTL["attempt_result"])

        return Response(data)

    @action(detail=True, methods=["post"])
    def grade(self, request, pk=None):
        """
        Manually set or override marks on individual answers.

        Used by teachers to grade short-answer questions that auto-grading
        could not fully evaluate.

        Expected request body::

            {
              "answer_grades": [
                { "answer_id": 12, "marks_awarded": 3 },
                { "answer_id": 17, "marks_awarded": 0 }
              ]
            }

        After grading, the attempt's total marks and percentage are
        recalculated and the attempt is marked GRADED.
        Teacher / Admin only.
        """
        attempt = self.get_object()

        if attempt.status == QuizAttempt.StatusChoices.IN_PROGRESS:
            return Response(
                {"error": "Cannot grade an attempt that has not been submitted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_grades = request.data.get("answer_grades", [])
        if not answer_grades:
            return Response(
                {"error": "answer_grades is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempt_answer_ids = set(
            StudentAnswer.objects.filter(attempt=attempt).values_list("id", flat=True)
        )

        with transaction.atomic():
            for item in answer_grades:
                answer_id    = item.get("answer_id")
                marks_awarded = item.get("marks_awarded")

                if answer_id not in attempt_answer_ids:
                    raise ValidationError(
                        f"Answer {answer_id} does not belong to this attempt."
                    )
                if marks_awarded is None or marks_awarded < 0:
                    raise ValidationError(
                        f"marks_awarded for answer {answer_id} must be a non-negative number."
                    )

                answer = StudentAnswer.objects.get(id=answer_id)

                if marks_awarded > answer.question.marks:
                    raise ValidationError(
                        f"marks_awarded ({marks_awarded}) exceeds the question's "
                        f"max marks ({answer.question.marks})."
                    )

                answer.marks_awarded = marks_awarded
                answer.is_correct    = marks_awarded > 0
                answer.save(update_fields=["marks_awarded", "is_correct"])

            # Recalculate attempt totals
            all_answers    = StudentAnswer.objects.filter(attempt=attempt)
            marks_obtained = sum(a.marks_awarded for a in all_answers)
            total_marks    = attempt.quiz.total_marks or 1   # prevent ZeroDivisionError

            attempt.marks_obtained = marks_obtained
            attempt.percentage     = round(marks_obtained / total_marks * 100, 2)
            attempt.status         = QuizAttempt.StatusChoices.GRADED
            attempt.save(update_fields=["marks_obtained", "percentage", "status"])

        invalidate_attempt_caches(attempt)

        return Response(
            QuizAttemptSerializer(attempt).data,
            status=status.HTTP_200_OK,
        )