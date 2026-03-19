from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('transactions/', views.transactions, name='transactions'),
    path('planning/', views.planning, name='planning'),
    path('settings/', views.settings, name='settings'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),

    path('delete-goal/', views.delete_goal, name='delete_goal'),
]
