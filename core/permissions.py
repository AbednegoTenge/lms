# permissions.py
from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """Allow only students"""
    def has_permission(self, request, view):
        return hasattr(request.user, 'student')


class IsTeacher(permissions.BasePermission):
    """Allow only teachers"""
    def has_permission(self, request, view):
        return hasattr(request.user, 'teacher')


class IsAdmin(permissions.BasePermission):
    """Allow admins and superusers"""
    def has_permission(self, request, view):
        return request.user.is_staff or request.user.is_superuser


class IsTeacherOrAdmin(permissions.BasePermission):
    """Allow teachers, admins, and superusers"""
    def has_permission(self, request, view):
        return (
            hasattr(request.user, 'teacher') or
            request.user.is_staff or
            request.user.is_superuser
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object or admins to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Admins can do anything
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Read permissions allowed to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only to owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'student'):
            return obj.student.user == request.user
        if hasattr(obj, 'teacher'):
            return obj.teacher.user == request.user
        
        return False


class IsEnrolledStudent(permissions.BasePermission):
    """Check if student is enrolled in the course"""
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'student'):
            return False
        
        student = request.user.student
        
        # For assignments and quizzes
        if hasattr(obj, 'course_offering'):
            from .models import Enrollment, AcademicTerm
            try:
                current_term = AcademicTerm.objects.get(is_current=True)
                return Enrollment.objects.filter(
                    student=student,
                    course_offering=obj.course_offering,
                    course_offering__term=current_term.term_number,
                    is_active=True
                ).exists()
            except AcademicTerm.DoesNotExist:
                return False
        
        return False


class IsTeacherOfCourse(permissions.BasePermission):
    """Check if teacher is assigned to the course"""
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'teacher'):
            return False
        
        teacher = request.user.teacher
        
        # For assignments and quizzes
        if hasattr(obj, 'teacher'):
            return obj.teacher == teacher
        
        return False