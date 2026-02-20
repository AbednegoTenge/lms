# # urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
     UserViewSet, StudentViewSet, TeacherViewSet, ProgrammeViewSet, CourseViewSet
    #  CourseViewSet, CourseOfferingViewSet, AcademicTermViewSet,
#     EnrollmentViewSet, AssignmentViewSet, SubmissionViewSet,
#     QuizViewSet, QuestionViewSet, QuizAttemptViewSet
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'students', StudentViewSet)
router.register(r'teachers', TeacherViewSet)
router.register(r'programmes', ProgrammeViewSet)
router.register(r'courses', CourseViewSet)
# router.register(r'course-offerings', CourseOfferingViewSet)
# router.register(r'academic-terms', AcademicTermViewSet)
# router.register(r'enrollments', EnrollmentViewSet)
# router.register(r'assignments', AssignmentViewSet)
# router.register(r'submissions', SubmissionViewSet)
# router.register(r'quizzes', QuizViewSet)
# router.register(r'questions', QuestionViewSet)
# router.register(r'quiz-attempts', QuizAttemptViewSet)

urlpatterns = [
     path('', include(router.urls)),
]