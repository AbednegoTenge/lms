
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserViewSet,
    StudentViewSet,
    TeacherViewSet,
    PrincipalViewSet,
    AdminViewSet,
    ProgrammeViewSet,
    CourseViewSet,
    CourseOfferingViewSet,
    AcademicTermViewSet,
    EnrollmentViewSet,
    AssignmentViewSet,
    SubmissionViewSet,
    QuizViewSet,
    CourseOutlineViewSet,
    CourseResourceViewSet,
    GradeWeightViewSet,
    QuestionViewSet,
    ChoiceViewSet,
    ShortAnswerKeyViewSet,
)

router = DefaultRouter()

router.register(r"users", UserViewSet, basename="user")
router.register(r"students", StudentViewSet, basename="student")
router.register(r"teachers", TeacherViewSet, basename="teacher")
router.register(r"principals", PrincipalViewSet, basename="principal")
router.register(r"admins", AdminViewSet, basename="admin")
router.register(r"programmes", ProgrammeViewSet, basename="programme")
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"offerings", CourseOfferingViewSet, basename="offering")
router.register(r"terms", AcademicTermViewSet, basename="term")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")
router.register(r"assignments", AssignmentViewSet, basename="assignment")
router.register(r"submissions", SubmissionViewSet, basename='submission')
router.register(r"quizzes", QuizViewSet, basename="quiz")
router.register(r"outlines", CourseOutlineViewSet, basename="outline")
router.register(r"resources", CourseResourceViewSet, basename="resource")
router.register(r"grade-weights", GradeWeightViewSet, basename="grade-weight")
router.register(r"questions", QuestionViewSet, basename="question")
router.register(r"choices", ChoiceViewSet, basename="choice")
router.register(r"answer-keys", ShortAnswerKeyViewSet, basename="answer-key")

urlpatterns = [
    path("", include(router.urls)),
]
