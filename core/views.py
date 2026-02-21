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

from .models import (
    User, Student, Teacher, Principal, Admin,
    Programme, Course, CourseOffering, AcademicTerm,
    Enrollment, Assignment, Submission, Quiz
)
from .serializers import (
    UserSerializer, StudentSerializer, TeacherSerializer, 
    PrincipalSerializer, ProgrammeSerializer, CourseSerializer, 
    CourseOfferingSerializer, AcademicTermSerializer, EnrollmentSerializer, 
    AssignmentSerializer, SubmissionSerializer, QuizSerializer
)
from .permissions import (
    IsTeacher, IsStudent, IsAdmin, IsTeacherOrAdmin, IsTeacherOfCourse
)


# ==================== HELPER FUNCTIONS ====================

def get_current_term():
    """Get current academic term or return None"""
    try:
        return AcademicTerm.objects.get(is_current=True)
    except AcademicTerm.DoesNotExist:
        return None


def check_user_role(user, expected_role):
    """Check if user has expected role, raise 403 if not"""
    if not hasattr(user, expected_role):
        raise PermissionDenied(f'User is not a {expected_role}')


def get_enrolled_course_offerings(student, term=None):
    """Get course offerings for enrolled student"""
    if term is None:
        term = get_current_term()
    
    if not term:
        return []
    
    return Enrollment.objects.filter(
        student=student,
        course_offering__term=term.term_number,
        is_active=True
    ).values_list('course_offering_id', flat=True)


# ==================== USER VIEWSET ====================

class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        elif self.action == 'login':
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        role = request.data.get('role')
        school_id = request.data.get('school_id')
        password = request.data.get('password')
        
        if not all([role, school_id, password]):
            return Response(
                {"error": "Role, school_id, and password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cache_key = f"login:{role}:{school_id}"
        user_data = cache.get(cache_key)
        
        if not user_data:
            try:
                user = User.objects.get(school_id=school_id)
            except User.DoesNotExist:
                return Response(
                    {"error": "Invalid credentials"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if not authenticate(request, username=school_id, password=password):
                return Response(
                    {"error": "Invalid credentials"}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if user.role != role:
                return Response(
                    {"error": f"User is not a {role}"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            refresh = RefreshToken.for_user(user)
            refresh['user_id'] = user.id
            refresh['role'] = role
            
            user_data = {
                "user_id": user.id,
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh)
            }
            
            cache.set(cache_key, user_data, timeout=60 * 60 * 4)
        
        return Response({
            "message": "Login successful", 
            **user_data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def me(self, request):
        cache_key = f"user_login_data:{request.user.id}"
        user_data = cache.get(cache_key)
        
        if not user_data:
            serializer = UserSerializer(request.user)
            user_data = serializer.data
            cache.set(cache_key, user_data, timeout=60 * 300)
        
        return Response({'user': user_data})
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        user = request.user
        role_map = {
            'student': lambda u: (u.student.student_number, 'student'),
            'teacher': lambda u: (u.teacher.employee_number, 'teacher'),
            'principal': lambda u: (u.principal.employee_number, 'principal'),
            'admin': lambda u: (u.admin.employee_number, 'admin')
        }
        
        for role_attr, get_data in role_map.items():
            if hasattr(user, role_attr):
                identifier, role = get_data(user)
                cache.delete(f"login:{role}:{identifier}")
                break
        
        cache.delete(f"user_login_data:{user.id}")
        return Response({"message": "Logged out successfully"})


# ==================== BASE PROFILE VIEWSET (Mixin) ====================

class ProfileViewSetMixin:
    """Mixin for common profile viewset methods"""
    
    def get_queryset_for_profile(self, model_class, user_attr, related_fields):
        """Generic queryset filtering for profile models"""
        user = self.request.user
        queryset = model_class.objects.select_related(*related_fields)
        
        if user.is_staff or user.is_superuser:
            return queryset.all()
        
        if hasattr(user, user_attr):
            return queryset.filter(user=user)
        
        return queryset.none()
    
    def get_me_action(self, user_attr, error_message):
        """Generic 'me' action"""
        check_user_role(self.request.user, user_attr)
        instance = getattr(self.request.user, user_attr)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ==================== STUDENT VIEWSET ====================

class StudentViewSet(ProfileViewSetMixin, ModelViewSet):
    queryset = Student.objects.select_related('user', 'programme').all()
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        elif self.action == 'me':
            return [IsAuthenticated(), IsStudent()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        queryset = Student.objects.select_related('user', 'programme')
        
        if user.is_staff or user.is_superuser:
            return queryset.all()
        
        if hasattr(user, 'student'):
            return queryset.filter(user=user)
        
        if hasattr(user, 'teacher'):
            student_ids = Enrollment.objects.filter(
                course_offering__in=user.teacher.assigned_course.all(),
                is_active=True
            ).values_list('student_id', flat=True).distinct()
            return queryset.filter(id__in=student_ids)
        
        return queryset.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        return self.get_me_action('student', 'User is not a student')
    
    def _check_student_access(self, student):
        """Check if user can access this student's data"""
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return True
        
        if hasattr(user, 'student') and user.student == student:
            return True
        
        if hasattr(user, 'teacher'):
            return student.enrollments.filter(
                course_offering__in=user.teacher.assigned_course.all(),
                is_active=True
            ).exists()
        
        raise PermissionDenied('You do not have access to this student')
    
    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        student = self.get_object()
        self._check_student_access(student)
        
        enrollments = Enrollment.objects.filter(
            student=student,
            is_active=True
        ).select_related('course_offering__course')
        
        serializer = EnrollmentSerializer(enrollments, many=True)
        
        return Response({
            'student': student.student_number,
            'student_name': student.user.get_full_name(),
            'total_enrollments': enrollments.count(),
            'enrollments': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        student = self.get_object()
        self._check_student_access(student)
        
        current_term = get_current_term()
        if not current_term:
            return Response(
                {'error': 'No current academic term set'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        enrolled_offerings = get_enrolled_course_offerings(student, current_term)
        assignments = Assignment.objects.filter(
            course_offering_id__in=enrolled_offerings,
            status=Assignment.StatusChoices.PUBLISHED
        ).select_related('course_offering__course')
        
        serializer = AssignmentSerializer(assignments, many=True)
        
        return Response({
            'student': student.student_number,
            'total_assignments': assignments.count(),
            'assignments': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        student = self.get_object()
        self._check_student_access(student)
        
        submissions = Submission.objects.filter(
            student=student
        ).select_related('assignment__course_offering__course')
        
        serializer = SubmissionSerializer(submissions, many=True)
        
        return Response({
            'student': student.student_number,
            'total_submissions': submissions.count(),
            'graded_submissions': submissions.filter(is_graded=True).count(),
            'submissions': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def by_programme(self, request):
        queryset = self.get_queryset()
        
        programme_id = request.query_params.get('programme')
        level = request.query_params.get('level')
        
        if programme_id:
            queryset = queryset.filter(programme_id=programme_id)
        if level:
            queryset = queryset.filter(level=int(level))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total_students': queryset.count(),
            'students': serializer.data
        })


# ==================== TEACHER VIEWSET ====================

class TeacherViewSet(ProfileViewSetMixin, ModelViewSet):
    queryset = Teacher.objects.select_related('user').prefetch_related('assigned_course').all()
    serializer_class = TeacherSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        elif self.action == 'me':
            return [IsAuthenticated(), IsTeacher()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Teacher.objects.select_related('user').prefetch_related('assigned_course')
        
        if user.is_staff or user.is_superuser:
            return queryset.all()
        
        if hasattr(user, 'teacher'):
            return queryset.filter(user=user)
        
        if hasattr(user, 'student'):
            course_offering_ids = Enrollment.objects.filter(
                student=user.student,
                is_active=True
            ).values_list('course_offering_id', flat=True)
            
            teacher_ids = Teacher.assigned_course.through.objects.filter(
                courseoffering_id__in=course_offering_ids
            ).values_list('teacher_id', flat=True).distinct()
            
            return queryset.filter(id__in=teacher_ids)
        
        return queryset.none()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        return self.get_me_action('teacher', 'User is not a teacher')
    
    @action(detail=True, methods=['get'])
    def courses(self, request, pk=None):
        teacher = self.get_object()
        courses = teacher.assigned_course.select_related('course').all()
        serializer = CourseOfferingSerializer(courses, many=True)
        
        return Response({
            'teacher': teacher.user.get_full_name(),
            'employee_number': teacher.employee_number,
            'total_courses': courses.count(),
            'courses': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        teacher = self.get_object()
        assignments = Assignment.objects.filter(
            teacher=teacher
        ).select_related('course_offering__course')
        
        serializer = AssignmentSerializer(assignments, many=True)
        
        return Response({
            'teacher': teacher.user.get_full_name(),
            'total_assignments': assignments.count(),
            'assignments': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        teacher = self.get_object()
        
        student_ids = Enrollment.objects.filter(
            course_offering__in=teacher.assigned_course.all(),
            is_active=True
        ).values_list('student_id', flat=True).distinct()
        
        students = Student.objects.filter(
            id__in=student_ids
        ).select_related('user', 'programme')
        
        serializer = StudentSerializer(students, many=True)
        
        return Response({
            'teacher': teacher.user.get_full_name(),
            'total_students': students.count(),
            'students': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def by_department(self, request):
        queryset = self.get_queryset()
        department = request.query_params.get('department')
        
        if department:
            queryset = queryset.filter(department__icontains=department)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total_teachers': queryset.count(),
            'teachers': serializer.data
        })


# ==================== PRINCIPAL VIEWSET ====================

class PrincipalViewSet(ProfileViewSetMixin, ModelViewSet):
    queryset = Principal.objects.select_related('user').all()
    serializer_class = PrincipalSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        return self.get_queryset_for_profile(Principal, 'principal', ['user'])
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        return self.get_me_action('principal', 'User is not a principal')
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        check_user_role(request.user, 'principal')
        
        stats = {
            'total_students': Student.objects.count(),
            'total_teachers': Teacher.objects.count(),
            'total_programmes': Programme.objects.count(),
            'active_assignments': 0,
            'active_quizzes': 0
        }
        
        current_term = get_current_term()
        if current_term:
            stats['active_assignments'] = Assignment.objects.filter(
                status=Assignment.StatusChoices.PUBLISHED,
                course_offering__term=current_term.term_number
            ).count()
            stats['active_quizzes'] = Quiz.objects.filter(
                status=Quiz.StatusChoices.PUBLISHED,
                course_offering__term=current_term.term_number
            ).count()
        
        return Response(stats)


# ==================== PROGRAMME VIEWSET ====================

class ProgrammeViewSet(ModelViewSet):
    queryset = Programme.objects.all()
    serializer_class = ProgrammeSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    @action(detail=True, methods=['get'])
    def students(self, request, pk=None):
        programme = self.get_object()
        students = programme.students.select_related('user').all()
        serializer = StudentSerializer(students, many=True)
        
        return Response({
            'programme': programme.name,
            'total_students': students.count(),
            'students': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def electives(self, request, pk=None):
        programme = self.get_object()
        level = request.query_params.get('level')
        term = request.query_params.get('term')
        
        electives = programme.elective_courses.all()
        
        if level and term:
            current_term = get_current_term()
            if not current_term:
                return Response(
                    {'error': 'No current academic term set'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            offerings = CourseOffering.objects.filter(
                course__in=electives,
                level=int(level),
                term=int(term),
                is_active=True
            ).select_related('course')
            
            serializer = CourseOfferingSerializer(offerings, many=True)
            
            return Response({
                'programme': programme.name,
                'level': int(level),
                'term': int(term),
                'available_electives': serializer.data
            })
        
        serializer = CourseSerializer(electives, many=True)
        return Response({
            'programme': programme.name,
            'total_electives': electives.count(),
            'electives': serializer.data
        })


# ==================== COURSE VIEWSET ====================

class CourseViewSet(ModelViewSet):
    queryset = Course.objects.prefetch_related('programmes').all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = Course.objects.prefetch_related('programmes').all()
        
        course_type = self.request.query_params.get('course_type')
        programme_id = self.request.query_params.get('programme')
        
        if course_type:
            queryset = queryset.filter(course_type=course_type.upper())
        if programme_id:
            queryset = queryset.filter(programmes__id=programme_id)
        
        return queryset.distinct()
    
    @action(detail=True, methods=['get'])
    def offerings(self, request, pk=None):
        course = self.get_object()
        offerings = CourseOffering.objects.filter(course=course, is_active=True)
        
        level = request.query_params.get('level')
        term = request.query_params.get('term')
        
        if level:
            offerings = offerings.filter(level=int(level))
        if term:
            offerings = offerings.filter(term=int(term))
        
        serializer = CourseOfferingSerializer(offerings, many=True)
        
        return Response({
            'course': course.name,
            'course_code': course.code_prefix,
            'total_offerings': offerings.count(),
            'offerings': serializer.data
        })


# ==================== COURSE OFFERING VIEWSET ====================

class CourseOfferingViewSet(ModelViewSet):
    queryset = CourseOffering.objects.select_related('course').all()
    serializer_class = CourseOfferingSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = CourseOffering.objects.select_related('course').all()
        user = self.request.user
        
        # Apply query param filters
        filters = {}
        for param in ['level', 'term', 'course_type', 'programme']:
            value = self.request.query_params.get(param)
            if value:
                if param == 'course_type':
                    filters['course__course_type'] = value.upper()
                elif param == 'programme':
                    filters['course__programmes__id'] = value
                else:
                    filters[param] = int(value)
        
        queryset = queryset.filter(**filters)
        
        # Role-based filtering
        if hasattr(user, 'student'):
            current_term = get_current_term()
            if current_term:
                queryset = queryset.filter(
                    term=current_term.term_number,
                    is_active=True
                )
        elif hasattr(user, 'teacher') and not filters:
            queryset = queryset.filter(
                id__in=user.teacher.assigned_course.values_list('id', flat=True)
            )
        
        return queryset.distinct()
    
    def _check_teaching_access(self, offering):
        """Check if user teaches this course"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return True
        
        if hasattr(self.request.user, 'teacher'):
            return self.request.user.teacher.assigned_course.filter(
                id=offering.id
            ).exists()
        
        raise PermissionDenied('Only teachers and admins can view enrollments')
    
    @action(detail=True, methods=['get'])
    def enrollments(self, request, pk=None):
        offering = self.get_object()
        self._check_teaching_access(offering)
        
        enrollments = Enrollment.objects.filter(
            course_offering=offering,
            is_active=True
        ).select_related('student__user')
        
        serializer = EnrollmentSerializer(enrollments, many=True)
        
        return Response({
            'course_code': offering.course_code,
            'course_name': offering.course.name,
            'level': offering.level,
            'term': offering.term,
            'total_enrolled': enrollments.count(),
            'enrollments': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def assignments(self, request, pk=None):
        offering = self.get_object()
        assignments = Assignment.objects.filter(
            course_offering=offering
        ).select_related('teacher__user')
        
        if hasattr(request.user, 'student'):
            assignments = assignments.filter(status=Assignment.StatusChoices.PUBLISHED)
        
        serializer = AssignmentSerializer(assignments, many=True)
        
        return Response({
            'course_code': offering.course_code,
            'course_name': offering.course.name,
            'total_assignments': assignments.count(),
            'assignments': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def quizzes(self, request, pk=None):
        offering = self.get_object()
        quizzes = Quiz.objects.filter(
            course_offering=offering
        ).select_related('teacher__user')
        
        if hasattr(request.user, 'student'):
            quizzes = quizzes.filter(status=Quiz.StatusChoices.PUBLISHED)
        
        serializer = QuizSerializer(quizzes, many=True)
        
        return Response({
            'course_code': offering.course_code,
            'course_name': offering.course.name,
            'total_quizzes': quizzes.count(),
            'quizzes': serializer.data
        })


# ==================== ENROLLMENT VIEWSET ====================

class EnrollmentViewSet(ModelViewSet):
    queryset = Enrollment.objects.select_related(
        'student__user',
        'course_offering__course'
    ).all()
    serializer_class = EnrollmentSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy', 'bulk_enroll']:
            return [IsAuthenticated(), IsAdmin()]
        elif self.action in ['update', 'partial_update', 'update_grade']:
            return [IsAuthenticated(), IsTeacherOrAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Enrollment.objects.select_related(
            'student__user',
            'course_offering__course'
        )
        
        if user.is_staff or user.is_superuser:
            return queryset.all()
        
        if hasattr(user, 'student'):
            current_term = get_current_term()
            if current_term:
                return queryset.filter(
                    student=user.student,
                    course_offering__term=current_term.term_number,
                    is_active=True
                )
            return queryset.filter(student=user.student, is_active=True)
        
        if hasattr(user, 'teacher'):
            return queryset.filter(
                course_offering__in=user.teacher.assigned_course.all()
            )
        
        return queryset.none()
    
    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        
        if self.action in ['update', 'partial_update']:
            if request.user.is_staff or request.user.is_superuser:
                return
            
            if hasattr(request.user, 'teacher'):
                is_teaching = request.user.teacher.assigned_course.filter(
                    id=obj.course_offering.id
                ).exists()
                
                if is_teaching:
                    allowed_fields = {'grade'}
                    requested_fields = set(request.data.keys())
                    
                    if not requested_fields.issubset(allowed_fields):
                        raise PermissionDenied("Teachers can only update the grade field.")
                    return
                else:
                    raise PermissionDenied("You are not teaching this course.")
            
            raise PermissionDenied("You don't have permission to modify enrollments.")
    
    @action(detail=False, methods=['get'])
    def my_enrollments(self, request):
        check_user_role(request.user, 'student')
        
        current_term = get_current_term()
        if not current_term:
            return Response(
                {'error': 'No current academic term set'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        enrollments = Enrollment.objects.filter(
            student=request.user.student,
            course_offering__term=current_term.term_number,
            is_active=True
        ).select_related('course_offering__course')
        
        serializer = self.get_serializer(enrollments, many=True)
        
        core_courses = [e for e in serializer.data if e['is_core']]
        elective_courses = [e for e in serializer.data if not e['is_core']]
        
        return Response({
            'term': current_term.term_number,
            'academic_year': current_term.academic_year,
            'core_courses': core_courses,
            'elective_courses': elective_courses,
            'total_courses': len(serializer.data)
        })
    
    @action(detail=False, methods=['post'])
    def bulk_enroll(self, request):
        student_ids = request.data.get('student_ids', [])
        course_offering_id = request.data.get('course_offering_id')
        is_core = request.data.get('is_core', False)
        
        if not student_ids or not course_offering_id:
            return Response(
                {'error': 'student_ids and course_offering_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course_offering = CourseOffering.objects.get(id=course_offering_id)
            students = Student.objects.filter(id__in=student_ids)
            
            if students.count() != len(student_ids):
                return Response(
                    {'error': 'Some student IDs are invalid'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            enrollments = []
            for student in students:
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    course_offering=course_offering,
                    defaults={'is_core': is_core}
                )
                if created:
                    enrollments.append(enrollment)
            
            return Response({
                'message': f'Successfully enrolled {len(enrollments)} students',
                'enrolled_count': len(enrollments)
            }, status=status.HTTP_201_CREATED)
            
        except CourseOffering.DoesNotExist:
            return Response(
                {'error': 'Course offering not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def update_grade(self, request, pk=None):
        enrollment = self.get_object()
        grade = request.data.get('grade')
        
        if not grade:
            return Response(
                {'error': 'Grade is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not (request.user.is_staff or request.user.is_superuser):
            if hasattr(request.user, 'teacher'):
                is_teaching = request.user.teacher.assigned_course.filter(
                    id=enrollment.course_offering.id
                ).exists()
                if not is_teaching:
                    return Response(
                        {'error': 'You are not teaching this course'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Only teachers and admins can update grades'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        enrollment.grade = grade
        enrollment.save(update_fields=['grade'])
        
        serializer = self.get_serializer(enrollment)
        return Response(serializer.data)


# ==================== ASSIGNMENT VIEWSET ====================

class AssignmentViewSet(ModelViewSet):
    queryset = Assignment.objects.select_related('course_offering__course', 'teacher__user').all()
    serializer_class = AssignmentSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsTeacher()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), (IsTeacherOfCourse | IsAdmin)]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Assignment.objects.select_related('course_offering__course', 'teacher__user')
        
        if user.is_staff or user.is_superuser:
            return queryset.all()
        
        if hasattr(user, 'teacher'):
            return queryset.filter(teacher=user.teacher)
        
        if hasattr(user, 'student'):
            current_term = get_current_term()
            if not current_term:
                return queryset.none()
            
            enrolled_offerings = get_enrolled_course_offerings(user.student, current_term)
            return queryset.filter(
                course_offering_id__in=enrolled_offerings,
                status=Assignment.StatusChoices.PUBLISHED
            )
        
        return queryset.none()
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher)