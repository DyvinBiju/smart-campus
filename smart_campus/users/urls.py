from django.urls import path

from .views import faculty_signup_view
from .views import student_signup_view

app_name = "users"
urlpatterns = [
    path("signup/student/", view=student_signup_view, name="student_signup"),
    path("signup/faculty/", view=faculty_signup_view, name="faculty_signup"),
]




