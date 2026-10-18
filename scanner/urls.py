from django.urls import path
from . import views

app_name = "scanner"
urlpatterns = [
    path('', views.home, name='home'),
    path('status/<uuid:uid>/', views.status, name='status'),
    path('page/<uuid:uid>/', views.pageDetails, name='details'),
    path('changes/<uuid:uid>/', views.changes, name='changes'),
]
