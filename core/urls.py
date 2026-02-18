from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('setup-goal/', views.setup_goal, name='goal_setup'),
    path('delete-goal/', views.delete_goal, name='delete_goal'),
    path('fixed-flows/', views.recurring_management, name='fixed_flows'),
    path('add/', views.add_transaction, name='transaction'),
    path('settings/', views.settings, name='settings'),

    path('api/transactions/', views.transaction_api, name='transaction_api'),
]
