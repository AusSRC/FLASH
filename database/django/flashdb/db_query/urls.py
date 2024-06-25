from django.urls import path
from . import views

urlpatterns = [
    path("",views.index, name="index"),
    path('query_database/', views.query_database, name='query_database'),
    path('show_aladin/', views.show_aladin, name="show_aladin"),
    path('my-url/', views.my_view, name='my-view'),
]
