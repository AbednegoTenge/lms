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

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student')
    student_number = models.CharField(max_length=20, unique=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    enrollment_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GenderChoices.choices)
    guardian_name = models.CharField(max_length=255, null=True, blank=True)
    guardian_contact = models.CharField(max_length=20, null=True, blank=True)
    level = models.CharField(max_length=50, null=True, blank=True)
    current_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    cumulative_gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        indexes = [
            models.Index(fields=['student_number']),
        ]

    def save(self, *args, **kwargs):
        from django.db import transaction
        with transaction.atomic():
            # Save first if new (to get ID)
            if not self.id:
                super().save(*args, **kwargs)

            # Generate student number if not set
            if not self.student_number:
                self.student_number = f"STD{str(self.id).zfill(3)}"

            # Final save to persist student_number
            super().save(*args, **kwargs)

            # Mirror to User.school_id
            if self.user and not self.user.school_id:
                self.user.school_id = self.student_number
                self.user.save(update_fields=['school_id'])


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


    def save(self, *args, **kwargs):
        from django.db import transaction
        with transaction.atomic():
            # Save first if new (to get ID)
            if not self.id:
                super().save(*args, **kwargs)
            if not self.employee_number:
                prefix = self.ROLE_PREFIX[self.__class__.__name__.lower()]
                self.employee_number = f"{prefix}{str(self.id).zfill(3)}"
            super().save(*args, **kwargs)
            if not self.user.school_id:
                self.user.school_id = self.employee_number
                self.user.save()
            

class Teacher(StaffBase):
    department = models.CharField(max_length=100, null=True, blank=True)

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