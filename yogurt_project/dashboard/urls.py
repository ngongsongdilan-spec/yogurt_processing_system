from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('app/', views.index, name='index'),
    path('api/login/', views.login_view, name='login'),
    path('api/signup/', views.signup_view, name='signup'),
    path('api/dashboard/', views.dashboard_data, name='dashboard'),
    path('api/inventory/', views.inventory_data, name='inventory'),
    path('api/batches/', views.batches_data, name='batches'),
    path('api/qc/', views.quality_control_view, name='qc'),
    path('api/machines/', views.machines_data, name='machines'),
    path('api/audit/', views.audit_data, name='audit'),
    path('api/purchasing/', views.purchasing_data, name='purchasing'),
    path('api/sales/', views.sales_data, name='sales'),
    path('api/trigger-test/', views.trigger_test_view, name='trigger_test'),
    path('api/sql-explorer/', views.sql_explorer, name='sql_explorer'),
]
