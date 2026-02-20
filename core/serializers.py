from rest_framework import serializers
from .models import (
    User, Student, Teacher, Principal,
    Programme, Course, CourseOffering, AcademicTerm, 
    Enrollment, Assignment, Submission, Quiz, Question, 
    Choice, ShortAnswerKey, QuizAttempt, StudentAnswer
)


class UserSerializer(serializers.ModelSerializer):
    """User serializer - handles both read and write"""
    role = serializers.ReadOnlyField()
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    password_confirm = serializers.CharField(write_only=True, required=False, min_length=8)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'school_id', 'role', 
            'is_active', 'is_staff', 'date_joined'
        ]
        read_only_fields = ['school_id', 'role', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def validate(self, data):
        # Only validate passwords if they're being set
        if 'password' in data or 'password_confirm' in data:
            if data.get('password') != data.get('password_confirm'):
                raise serializers.ValidationError({"password": "Passwords do not match"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class StudentSerializer(serializers.ModelSerializer):
    """Student serializer - handles everything"""
    user = UserSerializer()
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Student
        fields = [
            'id', 'user', 'full_name', 'student_number', 'date_of_birth',
            'enrollment_date', 'gender', 'guardian_name', 'guardian_contact',
            'level', 'current_gpa', 'cumulative_gpa'
        ]
        read_only_fields = ['student_number']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        student = Student.objects.create(user=user, **validated_data)
        return student
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        # Update user if data provided
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
        
        # Update student fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class TeacherSerializer(serializers.ModelSerializer):
    """Teacher serializer - handles everything"""
    user = UserSerializer()
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Teacher
        fields = [
            'id', 'user', 'full_name', 'employee_number', 'date_of_birth',
            'hire_date', 'contact_number', 'department'
        ]
        read_only_fields = ['employee_number']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        
        teacher = Teacher.objects.create(user=user, **validated_data)
        return teacher
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class PrincipalSerializer(serializers.ModelSerializer):
    """Principal serializer - handles everything"""
    user = UserSerializer()
    full_name = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Principal
        fields = [
            'id', 'user', 'full_name', 'employee_number',
            'date_of_birth', 'hire_date', 'contact_number'
        ]
        read_only_fields = ['employee_number']
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()
    
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        user.is_staff = True  # Principal should have staff access
        user.save()
        
        principal = Principal.objects.create(user=user, **validated_data)
        return principal
    
    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            user_serializer.is_valid(raise_exception=True)
            user_serializer.save()
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = ['id', 'name', 'code', 'description', 'max_electives_per_term']


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name', 'code_prefix', 'course_type', 'description', 'credits']


class CourseOfferingSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    course_code = serializers.CharField(read_only=True)
    course_type = serializers.CharField(source='course.course_type', read_only=True)
    
    class Meta:
        model = CourseOffering
        fields = ['id', 'course', 'course_name', 'course_code', 'course_type', 
                  'level', 'term', 'is_active']


class AcademicTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = ['id', 'name', 'academic_year', 'term_number', 'start_date', 
                  'end_date', 'is_current', 'elective_selection_open']


class EnrollmentSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course_offering.course_code', read_only=True)
    course_name = serializers.CharField(source='course_offering.course.name', read_only=True)
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'course_offering', 'course_code', 
                  'course_name', 'is_core', 'grade', 'is_active', 'enrolled_date']


class AssignmentSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course_offering.course_code', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    submission_count = serializers.IntegerField(read_only=True)
    graded_submission_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Assignment
        fields = ['id', 'course_offering', 'course_code', 'teacher', 'teacher_name',
                  'title', 'description', 'attachment', 'status', 'total_marks',
                  'due_date', 'max_attempts', 'submission_count', 'graded_submission_count',
                  'created_at', 'updated_at']
        read_only_fields = ['teacher', 'created_at', 'updated_at']


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'assignment_title', 'student', 'student_name',
                  'text_answer', 'file', 'status', 'marks_obtained', 'percentage',
                  'feedback', 'is_graded', 'submitted_at', 'attempt_number',
                  'graded_at', 'graded_by']
        read_only_fields = ['student', 'submitted_at', 'graded_at', 'graded_by', 'attempt_number']


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'answer', 'is_correct', 'order']


class ShortAnswerKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortAnswerKey
        fields = ['id', 'text']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)
    answer_keys = ShortAnswerKeySerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'quiz', 'question', 'question_type', 'marks', 'order',
                  'explanation', 'is_required', 'choices', 'answer_keys']


class QuizSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source='course_offering.course_code', read_only=True)
    teacher_name = serializers.CharField(source='teacher.user.get_full_name', read_only=True)
    total_marks = serializers.IntegerField(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'course_offering', 'course_code', 'teacher', 'teacher_name',
                  'title', 'description', 'status', 'duration_minutes', 'max_attempts',
                  'start_time', 'end_time', 'total_marks', 'questions', 
                  'created_at', 'updated_at']
        read_only_fields = ['teacher', 'created_at', 'updated_at']


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = ['id', 'question', 'selected_choice', 'selected_choices',
                  'text_answer', 'is_correct', 'marks_awarded']


class QuizAttemptSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.user.get_full_name', read_only=True)
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    answers = StudentAnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz', 'quiz_title', 'student', 'student_name',
                  'attempt_number', 'status', 'marks_obtained', 'percentage',
                  'started_at', 'submitted_at', 'answers']
        read_only_fields = ['student', 'attempt_number', 'started_at', 'submitted_at']

class TokenRefreshResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()