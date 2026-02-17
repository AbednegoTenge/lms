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