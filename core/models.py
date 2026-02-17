from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True)
    school_id = models.CharField(max_length=20, unique=True, null=True, blank=True)

    @property
    def role(self):
        if hasattr(self, 'student'):
            return 'student'
        elif hasattr(self, 'teacher'):
            return 'teacher'
        elif self.is_superuser:
            return 'superadmin'  
        elif self.is_staff:
            return 'admin'
        return 'user'
    
    
class Student(models.Model):
    class GenderChoices(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name='student')
    student_number = models.CharField(max_length=20, unique=True, blank=True)
    programme = models.ForeignKey('Programme', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    date_of_birth = models.DateField(null=True, blank=True)
    enrolled_courses = models.ManyToManyField('CourseOffering', through='Enrollment', related_name='enrolled_students')
    enrollment_date = models.DateField(auto_now_add=True)
    gender = models.CharField(max_length=10, choices=GenderChoices.choices)
    guardian_name = models.CharField(max_length=255, null=True, blank=True)
    guardian_contact = models.CharField(max_length=20, null=True, blank=True)
    
    # Changed from CharField to IntegerField to match CourseOffering.LEVEL_CHOICES
    level = models.IntegerField(
        default=1,
        choices=[
            (1, 'Level 1'),
            (2, 'Level 2'),
            (3, 'Level 3'),
        ]
    )
    
    current_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    cumulative_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        indexes = [
            models.Index(fields=['student_number']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.student_number})"


class StaffBase(models.Model):
    ROLE_PREFIX = {
        'teacher': 'TCH',
        'admin': 'ADM',
        'principal': 'PRN',
    }
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='%(class)s')
    employee_number = models.CharField(max_length=20, unique=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    contact_number = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        abstract = True

class Teacher(StaffBase):
    department = models.CharField(max_length=100, null=True, blank=True)
    assigned_course = models.ManyToManyField('CourseOffering', blank=True, related_name='teachers')

    class Meta:
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'
        indexes = [
            models.Index(fields=['employee_number']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"
    

class Admin(StaffBase):
    class Meta:
        verbose_name = 'Admin'
        verbose_name_plural = 'Admins'
        indexes = [
            models.Index(fields=['employee_number']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"
    

class Principal(StaffBase):
    class Meta:
        verbose_name = 'Principal'
        verbose_name_plural = 'Principals'
        indexes = [
            models.Index(fields=['employee_number']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"


class Programme(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    max_electives_per_term = models.IntegerField(default=4)
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """Base course without level/term - like 'Mathematics' or 'Literature'"""
    COURSE_TYPE_CHOICES = [
        ('CORE', 'Core Course'),
        ('ELECTIVE', 'Elective Course'),
    ]
    
    name = models.CharField(max_length=200)
    code_prefix = models.CharField(max_length=10, help_text="e.g., MTH, ENG, SCI")
    course_type = models.CharField(max_length=10, choices=COURSE_TYPE_CHOICES, db_index=True)
    description = models.TextField(blank=True)
    credits = models.IntegerField(default=3)
    
    # For elective courses
    programmes = models.ManyToManyField(
        Programme, 
        blank=True,
        related_name='elective_courses'
    )
    
    def __str__(self):
        return f"{self.code_prefix} - {self.name}"
    
    class Meta:
        ordering = ['course_type', 'name']


class CourseOffering(models.Model):
    """Specific offering of a course in a level and term"""
    TERM_CHOICES = [
        (1, 'Term 1'),
        (2, 'Term 2'),
        (3, 'Term 3'),
    ]
    
    LEVEL_CHOICES = [
        (1, 'Level 1'),
        (2, 'Level 2'),
        (3, 'Level 3'),
    ]
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='offerings')
    level = models.IntegerField(choices=LEVEL_CHOICES)
    term = models.IntegerField(choices=TERM_CHOICES)
    is_active = models.BooleanField(default=True)
    
    @property
    def course_code(self):
        """Generate course code like MTH101, ENG202, etc."""
        return f"{self.course.code_prefix}{self.level}0{self.term}"
    
    def __str__(self):
        return f"{self.course_code} - {self.course.name}"
    
    class Meta:
        unique_together = ['course', 'level', 'term']
        ordering = ['level', 'term', 'course__name']
        indexes = [
            models.Index(fields=['level', 'term']),
        ]


class AcademicTerm(models.Model):
    """Track current academic term"""
    name = models.CharField(max_length=50, help_text="e.g., Term 1 2024/2025")
    academic_year = models.CharField(max_length=9)
    term_number = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    elective_selection_open = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one current term
            AcademicTerm.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-start_date']


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course_offering = models.ForeignKey(CourseOffering, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_core = models.BooleanField(default=False)
    grade = models.CharField(max_length=2, blank=True, null=True)
    
    class Meta:
        unique_together = ['student', 'course_offering']
        ordering = ['-enrolled_date']
        indexes = [
            models.Index(fields=['student', 'is_core']),
            models.Index(fields=['course_offering']),
        ]
    
    def __str__(self):
        return f"{self.student.student_number} - {self.course_offering.course_code}"


class Assignment(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CLOSED = 'closed', 'Closed'

    course_offering = models.ForeignKey(
        CourseOffering, 
        on_delete=models.CASCADE, 
        related_name='assignments'
    )
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assignments'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to='assignments/', 
        null=True, 
        blank=True, 
        help_text="Optional file attachment for the assignment"
    )
    status = models.CharField(
        max_length=10, 
        choices=StatusChoices.choices, 
        default=StatusChoices.DRAFT
    )
    total_marks = models.PositiveIntegerField(default=100)
    due_date = models.DateTimeField(null=True, blank=True)
    max_attempts = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum number of submission attempts allowed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course_offering', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.course_offering.course_code} - {self.title}"
    
    @property
    def submission_count(self):
        return self.submissions.count()
    
    @property
    def computed_status(self):
        """Compute status based on due date and submissions"""
        from django.utils import timezone
        if self.status == self.StatusChoices.PUBLISHED and self.due_date:
            if timezone.now() > self.due_date:
                return self.StatusChoices.CLOSED
        return self.status

    @property
    def is_past_due(self):
        from django.utils import timezone
        return timezone.now() > self.due_date if self.due_date else False
    
    @property
    def graded_submission_count(self):
        return self.submissions.filter(is_graded=True).count()

    def clean(self):
        """Custom validation to ensure due_date is in the future when publishing"""
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.due_date and self.due_date < timezone.now():
            raise ValidationError("Due date cannot be in the past.")

class Submission(models.Model):
    class StatusChoices(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        GRADED = 'graded', 'Graded'
        RETURNED = 'returned', 'Returned'   # Teacher returned for revision

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    text_answer = models.TextField(
        blank=True,
        null=True,
        help_text="Written answer if applicable"
    )
    file = models.FileField(
        upload_to='submissions/',
        null=True,
        blank=True,
        help_text="File submission if applicable"
    )
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.SUBMITTED
    )
    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    feedback = models.TextField(
        blank=True,
        null=True,
        help_text="Teacher feedback on submission"
    )
    is_graded = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='graded_submissions'
    )

    class Meta:
        # A student can only submit once per assignment
        unique_together = ['assignment', 'student', 'attempt_number']
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['assignment', 'is_graded']),
            models.Index(fields=['student', 'status']),
        ]

    def __str__(self):
        return f"{self.student.student_number} - {self.assignment.title}"

    @property
    def percentage(self):
        """Calculate percentage score"""
        from decimal import Decimal
        return (self.marks_obtained / Decimal(self.assignment.total_marks)) * 100 if self.marks_obtained is not None else None

    def clean(self):
        from django.core.exceptions import ValidationError

        if not self.text_answer and not self.file:
            raise ValidationError("Submission must have either a text answer or a file.")
        
        if self.marks_obtained and self.marks_obtained > self.assignment.total_marks:
            raise ValidationError("Marks cannot exceed total marks.")

        # Block submission if past due
        if self.assignment.is_past_due:
            raise ValidationError("This assignment is past its due date and is no longer accepting submissions.")

        # Enforce attempt limit
        existing_attempts = Submission.objects.filter(
            assignment=self.assignment,
            student=self.student,
        )
        if self.pk:
            existing_attempts = existing_attempts.exclude(pk=self.pk)
        
        attempt_count = existing_attempts.count()

        if attempt_count >= self.assignment.max_attempts:
            raise ValidationError(
                f"Maximum submission attempts ({self.assignment.max_attempts}) reached for this assignment."
            )
        
        self.attempt_number = attempt_count + 1

    def save(self, *args, **kwargs):
        from django.utils import timezone

        self.clean()  # Ensure validation is run before saving
        # Graded check takes priority
        if self.is_graded:
            if not self.graded_at:
                self.graded_at = timezone.now()
            if self.status != self.StatusChoices.RETURNED:
                self.status = self.StatusChoices.GRADED
        self.graded_by = self.assignment.teacher
        super().save(*args, **kwargs)


class Quiz(models.Model):
    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CLOSED = 'closed', 'Closed'

    course_offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.CASCADE,
        related_name='quizzes'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quizzes'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT
    )
    duration_minutes = models.PositiveIntegerField(
        default=30,
        help_text="Time allowed to complete the quiz in minutes"
    )
    max_attempts = models.PositiveSmallIntegerField(default=1)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['course_offering', 'status']),
            models.Index(fields=['start_time', 'end_time']),
        ]

    def __str__(self):
        return f"{self.course_offering.course_code} - {self.title}"

    @property
    def total_marks(self):
        """Computed from sum of all question marks"""
        return self.questions.aggregate(
            total=models.Sum('marks')
        )['total'] or 0

    @property
    def is_active(self):
        from django.utils import timezone
        now = timezone.now()
        if self.status == self.StatusChoices.PUBLISHED:
            if self.start_time and self.end_time:
                return self.start_time <= now <= self.end_time
        return False

    @property
    def is_past_due(self):
        from django.utils import timezone
        return timezone.now() > self.end_time if self.end_time else False

    def clean(self):
        from django.core.exceptions import ValidationError
        from django.utils import timezone
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValidationError("End time must be after start time.")
            if self.end_time < timezone.now():
                raise ValidationError("End time cannot be in the past.")


class Question(models.Model):
    class QuestionType(models.TextChoices):
        MCQ_SINGLE = 'mcq_single', 'Multiple Choice (Single Answer)'
        MCQ_MULTIPLE = 'mcq_multiple', 'Multiple Choice (Multiple Answers)'
        TRUE_FALSE = 'true_false', 'True/False'
        SHORT_ANSWER = 'short_answer', 'Short Answer'

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question = models.TextField()
    question_type = models.CharField(
        max_length=15,
        choices=QuestionType.choices,
        default=QuestionType.MCQ_SINGLE
    )
    marks = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    explanation = models.TextField(
        blank=True,
        null=True,
        help_text="Optional explanation shown after the quiz is submitted"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether the student must answer this question"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        indexes = [
            models.Index(fields=['quiz', 'order']),
            models.Index(fields=['quiz', 'question_type']),
        ]

    def __str__(self):
        return f"Q{self.order}: {self.question[:50]}"

    @property
    def correct_choices(self):
        return self.choices.filter(is_correct=True)

    @property
    def is_auto_gradable(self):
        return self.question_type in [
            self.QuestionType.MCQ_SINGLE,
            self.QuestionType.MCQ_MULTIPLE,
            self.QuestionType.TRUE_FALSE,
            self.QuestionType.SHORT_ANSWER,  # graded via answer keys
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quiz.status != Quiz.StatusChoices.DRAFT:
            raise ValidationError("Questions can only be added or edited while the quiz is in Draft status.")

    def save(self, *args, **kwargs):
        if not self.order:
            last = Question.objects.filter(quiz=self.quiz).order_by('order').last()
            self.order = (last.order + 1) if last else 1
        self.full_clean()
        super().save(*args, **kwargs)


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='choices'
    )
    answer = models.TextField()
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.answer} ({'Correct' if self.is_correct else 'Wrong'})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.question.quiz.status != Quiz.StatusChoices.DRAFT:
            raise ValidationError("Choices can only be added or edited while the quiz is in Draft status.")

        # Short answer questions should not have choices
        if self.question.question_type == Question.QuestionType.SHORT_ANSWER:
            raise ValidationError("Short answer questions cannot have choices.")

        # MCQ single can only have one correct answer
        if self.question.question_type == Question.QuestionType.MCQ_SINGLE and self.is_correct:
            existing_correct = Choice.objects.filter(
                question=self.question,
                is_correct=True
            )
            if self.pk:
                existing_correct = existing_correct.exclude(pk=self.pk)
            if existing_correct.exists():
                raise ValidationError("Single answer MCQ can only have one correct answer.")

        # True/False choices must be 'True' or 'False'
        if self.question.question_type == Question.QuestionType.TRUE_FALSE:
            if self.answer.strip().lower() not in ['true', 'false']:
                raise ValidationError("True/False choices must be 'True' or 'False'.")
            existing_choices = Choice.objects.filter(question=self.question)
            if self.pk:
                existing_choices = existing_choices.exclude(pk=self.pk)
            if existing_choices.count() >= 2:
                raise ValidationError("True/False questions can only have 2 choices.")

        # MCQ multiple must have at least 2 correct answers when quiz is published
        # We only warn here since choices are added one at a time
        if self.question.question_type == Question.QuestionType.MCQ_MULTIPLE and self.is_correct:
            pass  # no restriction, teacher decides how many correct answers

    def save(self, *args, **kwargs):
        if not self.order:
            last = Choice.objects.filter(question=self.question).order_by('order').last()
            self.order = (last.order + 1) if last else 1
        self.full_clean()
        super().save(*args, **kwargs)


class ShortAnswerKey(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='answer_keys'
    )
    text = models.CharField(
        max_length=500,
        help_text="An accepted answer for this question"
    )

    class Meta:
        unique_together = ['question', 'text']

    def __str__(self):
        return f"{self.question} → {self.text}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.question.question_type != Question.QuestionType.SHORT_ANSWER:
            raise ValidationError("Answer keys can only be added to short answer questions.")
        if self.question.quiz.status != Quiz.StatusChoices.DRAFT:
            raise ValidationError("Answer keys can only be added while the quiz is in Draft status.")

    def save(self, *args, **kwargs):
        # Normalize before saving so duplicates are caught consistently
        self.text = self.text.strip().lower()
        self.full_clean()
        super().save(*args, **kwargs)


class QuizAttempt(models.Model):
    class StatusChoices(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'In Progress'
        SUBMITTED = 'submitted', 'Submitted'
        GRADED = 'graded', 'Graded'

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='quiz_attempts'
    )
    attempt_number = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.IN_PROGRESS
    )
    marks_obtained = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['quiz', 'student', 'attempt_number']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.student_number} - {self.quiz.title} (Attempt {self.attempt_number})"

    @property
    def is_time_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        if self.started_at and self.quiz.duration_minutes:
            deadline = self.started_at + timedelta(minutes=self.quiz.duration_minutes)
            return timezone.now() > deadline
        return False

    @property
    def is_fully_graded(self):
        return not self.answers.filter(marks_awarded__isnull=True).exists()

    @property
    def percentage(self):
        from decimal import Decimal
        if self.marks_obtained is not None and self.quiz.total_marks > 0:
            return (self.marks_obtained / Decimal(self.quiz.total_marks)) * 100
        return None

    def auto_grade_all(self):
        """Grade all answers and calculate total marks"""
        for answer in self.answers.select_related('question'):
            answer.auto_grade()
        self.calculate_marks()

    def calculate_marks(self):
        from django.db.models import Sum
        total = self.answers.aggregate(total=Sum('marks_awarded'))['total'] or 0
        self.marks_obtained = total
        self.status = self.StatusChoices.GRADED if self.is_fully_graded else self.StatusChoices.SUBMITTED
        self.save()

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.pk:
            return

        if not self.quiz.is_active:
            raise ValidationError("This quiz is not currently active.")

        attempt_count = QuizAttempt.objects.filter(
            quiz=self.quiz,
            student=self.student
        ).count()

        if attempt_count >= self.quiz.max_attempts:
            raise ValidationError(
                f"Maximum attempts ({self.quiz.max_attempts}) reached for this quiz."
            )

        self.attempt_number = attempt_count + 1

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if self.status == self.StatusChoices.SUBMITTED and not self.submitted_at:
            self.submitted_at = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='student_answers'
    )
    # For MCQ single and True/False
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="For single answer MCQ and True/False"
    )
    # For MCQ multiple
    selected_choices = models.ManyToManyField(
        Choice,
        blank=True,
        related_name='multi_answer_selections',
        help_text="For multiple answer MCQ"
    )
    # For short answer
    text_answer = models.TextField(
        null=True,
        blank=True,
        help_text="For short answer questions"
    )
    is_correct = models.BooleanField(null=True, blank=True)
    marks_awarded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"{self.attempt.student.student_number} - {self.question}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.selected_choice and self.selected_choice.question != self.question:
            raise ValidationError("Selected choice does not belong to this question.")

        if self.question.question_type == Question.QuestionType.MCQ_SINGLE:
            if not self.selected_choice:
                raise ValidationError("Single answer MCQ requires a selected choice.")
            if self.text_answer:
                raise ValidationError("Single answer MCQ should not have a text answer.")

        if self.question.question_type == Question.QuestionType.TRUE_FALSE:
            if not self.selected_choice:
                raise ValidationError("True/False questions require a selected choice.")
            if self.text_answer:
                raise ValidationError("True/False questions should not have a text answer.")

        if self.question.question_type == Question.QuestionType.SHORT_ANSWER:
            if not self.text_answer:
                raise ValidationError("Short answer questions require a text answer.")
            if self.selected_choice:
                raise ValidationError("Short answer questions should not have a selected choice.")

        # MCQ multiple validation is handled post-save via selected_choices M2M

    def auto_grade(self):
        question_type = self.question.question_type

        if question_type == Question.QuestionType.MCQ_SINGLE:
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
                self.marks_awarded = self.question.marks if self.is_correct else 0
                self.save()

        elif question_type == Question.QuestionType.TRUE_FALSE:
            if self.selected_choice:
                self.is_correct = self.selected_choice.is_correct
                self.marks_awarded = self.question.marks if self.is_correct else 0
                self.save()

        elif question_type == Question.QuestionType.MCQ_MULTIPLE:
            correct_choice_ids = set(
                self.question.correct_choices.values_list('id', flat=True)
            )
            selected_choice_ids = set(
                self.selected_choices.values_list('id', flat=True)
            )

            if not selected_choice_ids:
                self.is_correct = False
                self.marks_awarded = 0
                self.save()
                return

            # All correct choices selected and no wrong ones = full marks
            if selected_choice_ids == correct_choice_ids:
                self.is_correct = True
                self.marks_awarded = self.question.marks

            # Partial: only award marks for each correct choice selected
            # deduct for wrong ones, floor at 0
            else:
                correct_selected = selected_choice_ids & correct_choice_ids
                wrong_selected = selected_choice_ids - correct_choice_ids
                total_correct = len(correct_choice_ids)

                mark_per_correct = self.question.marks / total_correct
                partial_marks = (len(correct_selected) - len(wrong_selected)) * mark_per_correct
                self.marks_awarded = max(partial_marks, 0)
                self.is_correct = False  # not fully correct

            self.save()

        elif question_type == Question.QuestionType.SHORT_ANSWER:
            if not self.text_answer:
                self.is_correct = False
                self.marks_awarded = 0
                self.save()
                return

            student_answer = self.text_answer.strip().lower()

            # Answer keys are already stored normalized (see ShortAnswerKey.save)
            accepted_answers = self.question.answer_keys.values_list('text', flat=True)

            self.is_correct = student_answer in accepted_answers
            self.marks_awarded = self.question.marks if self.is_correct else 0
            self.save()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)