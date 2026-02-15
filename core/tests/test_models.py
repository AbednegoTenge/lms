import pytest
from core.models import Student, Teacher, Principal, Admin
from django.contrib.auth import get_user_model

@pytest.mark.django_db
def test_student_creation():
    User = get_user_model()
    user = User.objects.create_user(username='student1', password='testpass')
    student = Student.objects.create(user=user, date_of_birth='2000-01-01')
    
    assert student.student_number.startswith('STD')
    assert student.user.school_id == student.student_number

@pytest.mark.django_db
def test_teacher_creation():
    User = get_user_model()
    user = User.objects.create_user(username='teacher1', password='testpass')
    teacher = Teacher.objects.create(user=user, date_of_birth='1980-01-01', hire_date='2010-01-01')
    
    assert teacher.employee_number.startswith('TCH')
    assert teacher.user.school_id == teacher.employee_number

@pytest.mark.django_db
def test_admin_creation():
    User = get_user_model()
    user = User.objects.create_user(username='admin1', password='testpass')
    admin = Admin.objects.create(user=user, date_of_birth='1975-01-01', hire_date='2005-01-01')
    
    assert admin.employee_number.startswith('ADM')
    assert admin.user.school_id == admin.employee_number

@pytest.mark.django_db
def test_principal_creation():
    User = get_user_model()
    user = User.objects.create_user(username='principal1', password='testpass')
    principal = Principal.objects.create(user=user, date_of_birth='1970-01-01', hire_date='2000-01-01')
    
    assert principal.employee_number.startswith('PRN')
    assert principal.user.school_id == principal.employee_number