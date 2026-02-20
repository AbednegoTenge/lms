# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Student, Teacher, Admin, Principal, 
    Programme, Course, CourseOffering, AcademicTerm, 
    Enrollment, Submission, Assignment, Quiz, Question, 
    Choice, ShortAnswerKey, QuizAttempt, StudentAnswer
)
from django import forms
from django.db.models import Q

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
    

class EnrollmentInlineForm(forms.ModelForm):
    """Filter course offerings by student's programme and level"""

    class Meta:
        model = Enrollment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        student = getattr(self, 'parent_instance', None)

        if student and student.programme:
            try:
                current_term = AcademicTerm.objects.get(is_current=True)

                self.fields['course_offering'].queryset = CourseOffering.objects.filter(
                    Q(course__programmes=student.programme) |  # Programme electives
                    Q(course__course_type='CORE'),              # OR all core courses
                    level=student.level,
                    term=current_term.term_number,
                    is_active=True
                ).select_related('course').order_by('course__course_type', 'course__name')

            except AcademicTerm.DoesNotExist:
                self.fields['course_offering'].queryset = CourseOffering.objects.filter(
                    course__programmes=student.programme,
                    level=student.level,
                    is_active=True
                ).select_related('course')
        else:
            self.fields['course_offering'].queryset = CourseOffering.objects.none()

class EnrollmentInline(admin.TabularInline):
    model = Enrollment
    form = EnrollmentInlineForm
    extra = 5
    fields = ['course_offering', 'is_core', 'grade', 'is_active']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.parent_instance = obj  # always pass student
        return formset

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    inlines = [EnrollmentInline]
    list_display = ['student_number', 'get_full_name', 'programme', 'level', 'enrollment_date']
    list_filter = ['programme', 'level', 'gender']
    search_fields = ['student_number', 'user__first_name', 'user__last_name']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'get_course_code', 'get_course_name', 'is_core', 'grade', 'is_active']
    list_filter = ['is_core', 'is_active', 'course_offering__level', 'course_offering__term']
    search_fields = ['student__student_number', 'student__user__first_name', 'course_offering__course__name']
    
    def get_course_code(self, obj):
        return obj.course_offering.course_code
    get_course_code.short_description = 'Course Code'
    
    def get_course_name(self, obj):
        return obj.course_offering.course.name
    get_course_name.short_description = 'Course Name'
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course_offering":
            # Get student_id from URL if editing enrollment
            if request.resolver_match.kwargs.get('object_id'):
                try:
                    enrollment = Enrollment.objects.get(pk=request.resolver_match.kwargs['object_id'])
                    student = enrollment.student
                    
                    # ✅ Filter by student's programme and level
                    if student.programme:
                        current_term = AcademicTerm.objects.get(is_current=True)
                        kwargs["queryset"] = CourseOffering.objects.filter(
                            course__programmes=student.programme,
                            level=student.level,
                            term=current_term.term_number,
                            is_active=True
                        ).select_related('course')
                except (Enrollment.DoesNotExist, AcademicTerm.DoesNotExist):
                    pass
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    # Show role in the list table
    list_display = (
        "username",
        "email",
        "school_id",
        "role",          # <- computed property
        "is_staff",
    )

    # Make role read-only in detail page
    readonly_fields = ("role",)

    # Add role + school_id to the main user info section
    fieldsets = BaseUserAdmin.fieldsets + (
        ("School Information", {"fields": ("school_id", "role")}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("School Information", {"fields": ("school_id",)}),
    )


class SubmissionInline(admin.TabularInline):
    model = Submission
    extra = 0
    fields = ['student', 'status', 'marks_obtained', 'is_graded', 'submitted_at']
    readonly_fields = ['student', 'submitted_at', 'status']

    def has_add_permission(self, request, obj=None):
        return False  # Submissions are created by students, not admin


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    inlines = [SubmissionInline]
    list_display = [
        'title', 'course_offering', 'teacher', 'status',
        'due_date', 'total_marks', 'submission_count', 'graded_count'
    ]
    list_filter = [
        'status',
        'course_offering__level',
        'course_offering__term',
    ]
    search_fields = ['title', 'course_offering__course__name', 'teacher__user__first_name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Assignment Details', {
            'fields': ('course_offering', 'teacher', 'title', 'description', 'attachment')
        }),
        ('Settings', {
            'fields': ('status', 'total_marks', 'due_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def submission_count(self, obj):
        return obj.submission_count
    submission_count.short_description = 'Submissions'

    def graded_count(self, obj):
        return obj.graded_submission_count
    graded_count.short_description = 'Graded'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Only show active course offerings"""
        if db_field.name == "course_offering":
            kwargs["queryset"] = CourseOffering.objects.filter(
                is_active=True
            ).select_related('course')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'assignment', 'status',
        'marks_obtained', 'percentage', 'is_graded', 'submitted_at'
    ]
    list_filter = ['status', 'is_graded', 'assignment__course_offering__level']
    search_fields = [
        'student__student_number',
        'student__user__first_name',
        'assignment__title'
    ]
    readonly_fields = ['submitted_at', 'graded_at', 'percentage']

    fieldsets = (
        ('Submission Info', {
            'fields': ('assignment', 'student', 'status', 'submitted_at')
        }),
        ('Submission Content', {
            'fields': ('text_answer', 'file')
        }),
        ('Grading', {
            'fields': ('is_graded', 'marks_obtained', 'percentage', 'feedback', 'graded_by', 'graded_at')
        }),
    )

    def percentage(self, obj):
        p = obj.percentage
        return f"{p:.1f}%" if p else "-"
    percentage.short_description = 'Score %'

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1
    fields = ['answer', 'is_correct', 'order']
    ordering = ['order']


class ShortAnswerKeyInline(admin.TabularInline):
    model = ShortAnswerKey
    extra = 1
    fields = ['text']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['question', 'question_type', 'marks', 'order', 'is_required']
    ordering = ['order']
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course_offering', 'teacher', 'status',
        'get_total_marks', 'duration_minutes', 'max_attempts',
        'start_time', 'end_time', 'is_active', 'is_past_due'
    ]
    list_filter = ['status', 'course_offering', 'teacher']
    search_fields = ['title', 'description', 'course_offering__course_code']
    readonly_fields = ['get_total_marks', 'is_active', 'is_past_due', 'created_at', 'updated_at']
    inlines = [QuestionInline]

    fieldsets = (
        ('Basic Info', {
            'fields': ('course_offering', 'teacher', 'title', 'description')
        }),
        ('Settings', {
            'fields': ('status', 'duration_minutes', 'max_attempts')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time')
        }),
        ('Computed', {
            'fields': ('get_total_marks', 'is_active', 'is_past_due', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_total_marks(self, obj):
        if not obj or not obj.pk:
            return '-'
        return obj.total_marks
    get_total_marks.short_description = 'Total Marks'

    def is_active(self, obj):
        if not obj or not obj.pk:
            return '-'
        return 'Yes' if obj.is_active else 'No'
    is_active.short_description = 'Active'

    def is_past_due(self, obj):
        if not obj or not obj.pk:
            return '-'
        return 'Yes' if obj.is_past_due else 'No'
    is_past_due.short_description = 'Past Due'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'quiz', 'text_preview', 'question_type',
        'marks', 'is_required', 'get_is_auto_gradable'
    ]
    list_filter = ['question_type', 'is_required', 'quiz']
    search_fields = ['question', 'quiz__title']
    readonly_fields = ['get_is_auto_gradable', 'created_at', 'updated_at']
    ordering = ['quiz', 'order']

    fieldsets = (
        ('Question', {
            'fields': ('quiz', 'question', 'question_type', 'marks', 'order', 'is_required')
        }),
        ('Extra', {
            'fields': ('explanation', 'get_is_auto_gradable', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.question_type == Question.QuestionType.SHORT_ANSWER:
            return [ShortAnswerKeyInline]
        return [ChoiceInline]

    def text_preview(self, obj):
        return obj.question[:60] + '...' if len(obj.question) > 60 else obj.question
    text_preview.short_description = 'Question'

    def get_is_auto_gradable(self, obj):
        if not obj or not obj.pk:
            return '-'
        return 'Yes' if obj.is_auto_gradable else 'No'
    get_is_auto_gradable.short_description = 'Auto Gradable'


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['answer', 'question', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__quiz']
    search_fields = ['answer', 'question__question']
    ordering = ['question', 'order']


@admin.register(ShortAnswerKey)
class ShortAnswerKeyAdmin(admin.ModelAdmin):
    list_display = ['text', 'question']
    search_fields = ['text', 'question__text']
    list_filter = ['question__quiz']


class StudentAnswerInline(admin.TabularInline):
    model = StudentAnswer
    extra = 0
    readonly_fields = [
        'question', 'selected_choice', 'text_answer',
        'is_correct', 'marks_awarded'
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'quiz', 'attempt_number', 'status',
        'marks_obtained', 'get_percentage', 'get_is_time_expired',
        'started_at', 'submitted_at'
    ]
    list_filter = ['status', 'quiz', 'quiz__course_offering']
    search_fields = ['student__student_number', 'quiz__title']
    readonly_fields = [
        'attempt_number', 'started_at', 'submitted_at',
        'get_percentage', 'get_is_time_expired', 'get_is_fully_graded'
    ]
    inlines = [StudentAnswerInline]

    fieldsets = (
        ('Attempt Info', {
            'fields': ('quiz', 'student', 'attempt_number', 'status')
        }),
        ('Marks', {
            'fields': ('marks_obtained', 'get_percentage')
        }),
        ('Timing', {
            'fields': ('started_at', 'submitted_at', 'get_is_time_expired')
        }),
        ('Grading', {
            'fields': ('get_is_fully_graded',),
            'classes': ('collapse',)
        }),
    )

    actions = ['grade_selected_attempts']

    def get_percentage(self, obj):
        if not obj or not obj.pk:
            return '-'
        p = obj.percentage
        return f'{p:.1f}%' if p is not None else '-'
    get_percentage.short_description = 'Percentage'

    def get_is_time_expired(self, obj):
        if not obj or not obj.pk:
            return '-'
        return 'Yes' if obj.is_time_expired else 'No'
    get_is_time_expired.short_description = 'Time Expired'

    def get_is_fully_graded(self, obj):
        if not obj or not obj.pk:
            return '-'
        return 'Yes' if obj.is_fully_graded else 'No'
    get_is_fully_graded.short_description = 'Fully Graded'

    def grade_selected_attempts(self, request, queryset):
        for attempt in queryset:
            attempt.auto_grade_all()
        self.message_user(request, f"{queryset.count()} attempt(s) graded successfully.")
    grade_selected_attempts.short_description = "Grade selected attempts"


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = [
        'get_student', 'get_question', 'get_answer',
        'is_correct', 'marks_awarded'
    ]
    list_filter = ['is_correct', 'question__question_type', 'attempt__quiz']
    search_fields = [
        'attempt__student__student_number',
        'question__text',
        'text_answer'
    ]
    readonly_fields = [
        'attempt', 'question', 'selected_choice',
        'text_answer', 'is_correct', 'marks_awarded'
    ]

    def has_add_permission(self, request):
        return False

    def get_student(self, obj):
        return obj.attempt.student.student_number
    get_student.short_description = 'Student'

    def get_question(self, obj):
        text = obj.question.text
        return text[:50] + '...' if len(text) > 50 else text
    get_question.short_description = 'Question'

    def get_answer(self, obj):
        if obj.text_answer:
            return obj.text_answer[:60]
        if obj.selected_choice:
            return obj.selected_choice.text
        choices = obj.selected_choices.all()
        if choices.exists():
            return ', '.join(c.text for c in choices)
        return '-'

admin.site.register(Admin)
admin.site.register(Principal)