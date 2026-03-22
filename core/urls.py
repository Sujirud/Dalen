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

    path('categories/add/', views.add_category, name='add_category'),
    path('categories/delete/', views.delete_category, name='delete_category'),

    path('transactions/edit/', views.edit_transactions, name='edit_transactions'),
    path('transactions/delete/', views.delete_transactions, name='delete_transactions'),

    path('recurring/add/', views.add_recurring, name='add_recurring'),
    path('recurring/delete/', views.delete_recurring, name='delete_recurring'),

    path('delete-goal/', views.delete_goal, name='delete_goal'),
]
