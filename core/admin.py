# admin.py
from django.contrib import admin
from .models import (
    User, Student, Teacher, Admin, Principal, 
    Programme, Course, CourseOffering, AcademicTerm, Enrollment
)

@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'max_electives_per_term']
    search_fields = ['name', 'code']

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code_prefix', 'name', 'course_type', 'credits']
    list_filter = ['course_type']
    search_fields = ['name', 'code_prefix']
    filter_horizontal = ['programmes']

@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ['get_course_code', 'course', 'level', 'term', 'is_active']
    list_filter = ['level', 'term', 'is_active', 'course__course_type']
    search_fields = ['course__name', 'course__code_prefix']
    
    def get_course_code(self, obj):
        return obj.course_code
    get_course_code.short_description = 'Course Code'
    get_course_code.admin_order_field = 'course__code_prefix'

@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ['name', 'academic_year', 'term_number', 'start_date', 'end_date', 'is_current', 'elective_selection_open']
    list_filter = ['is_current', 'elective_selection_open', 'academic_year']
    
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_number', 'get_full_name', 'programme', 'level', 'get_enrolled_courses', 'enrollment_date']
    list_filter = ['programme', 'level', 'gender']
    search_fields = ['student_number', 'user__first_name', 'user__last_name', 'user__email']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

    def get_enrolled_courses(self, obj):
        courses = obj.enrolled_courses.all()
        if not courses:
            return 'No courses found'
        return ','.join([course.course_code for course in courses])
    get_enrolled_courses.short_description = 'Enrolled Courses Count'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'get_course_code', 'is_core', 'grade', 'enrolled_date', 'is_active']
    list_filter = ['is_core', 'is_active', 'course_offering__level', 'course_offering__term']
    search_fields = ['student__student_number', 'student__user__first_name', 'course_offering__course__name']
    
    def get_course_code(self, obj):
        return obj.course_offering.course_code
    get_course_code.short_description = 'Course Code'


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['employee_number', 'get_full_name', 'department', 'get_assigned_courses']
    search_fields = ['employee_number', 'user__first_name', 'user__last_name', 'user__email']
    filter_horizontal = ['assigned_course']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

    def get_assigned_courses(self, obj):
        # Returns a comma-separated list of course codes
        courses = obj.assigned_course.all()
        if not courses:
            return 'No courses assigned'
        return ', '.join([course.course_code for course in courses])
    get_assigned_courses.short_description = 'Assigned Courses'



admin.site.register(User)
admin.site.register(Admin)
admin.site.register(Principal)