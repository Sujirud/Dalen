from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Auth & Public
    path('', views.landing, name='landing'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='landing'), name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Transactions & Categories
    path('transactions/', views.transactions, name='transactions'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('transactions/edit/', views.edit_transactions, name='edit_transactions'),
    path('transactions/delete/', views.delete_transactions, name='delete_transactions'),

    path('categories/add/', views.add_category, name='add_category'),
    path('categories/delete/', views.delete_category, name='delete_category'),

    # Planning
    path('planning/', views.planning, name='planning'),

    # Goals
    path('goal/add/', views.add_goal, name='add_goal'),
    path('goal/add/<str:type>/', views.add_goal, name='add_goal_by_type'),
    path('goal/edit/', views.edit_goal, name='edit_goal'),
    path('goal/delete/', views.delete_goal, name='delete_goal'),
    path('goal/complete/', views.complete_goal, name='complete_goal'),

    # Recurring Items
    path('recurring/add/', views.add_recurring, name='add_recurring'),
    path('recurring/delete/', views.delete_recurring, name='delete_recurring'),

    # Settings
    path('settings/', views.settings, name='settings'),
]
