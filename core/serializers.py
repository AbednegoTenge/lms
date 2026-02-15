from rest_framework import serializers
from .models import User, Student, Teacher, Principal


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