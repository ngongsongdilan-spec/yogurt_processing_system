from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('app/', views.index, name='index'),
    path('api/login/', views.login_view, name='login'),
    path('api/signup/', views.signup_view, name='signup'),
    path('api/dashboard/', views.dashboard_data, name='dashboard'),
    path('api/inventory/', views.inventory_data, name='inventory'),
    path('api/inventory/<int:item_id>/', views.inventory_item_view, name='inventory_item'),
    path('api/products/<int:item_id>/', views.product_item_view, name='product_item'),
    path('api/batches/', views.batches_data, name='batches'),
    path('api/batches/<int:batch_id>/', views.batch_detail_view, name='batch_detail'),
    path('api/qc/', views.quality_control_view, name='qc'),
    path('api/qc/<int:qcid>/', views.qc_detail_view, name='qc_detail'),
    path('api/machines/', views.machines_data, name='machines'),
    path('api/machines/<int:machine_id>/', views.machine_detail_view, name='machine_detail'),
    path('api/audit/', views.audit_data, name='audit'),
    path('api/purchasing/', views.purchasing_data, name='purchasing'),
    path('api/purchasing/<int:poid>/', views.purchasing_detail_view, name='purchasing_detail'),
    path('api/sales/', views.sales_data, name='sales'),
    path('api/sales/<int:sales_id>/', views.sales_detail_view, name='sales_detail'),
    path('api/trigger-test/', views.trigger_test_view, name='trigger_test'),
    path('api/sql-explorer/', views.sql_explorer, name='sql_explorer'),
    path('api/users/', views.users_view, name='users'),
    path('api/users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('api/ref-data/', views.ref_data, name='ref_data'),
]
