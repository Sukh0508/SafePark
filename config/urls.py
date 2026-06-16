"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from main.views import Home ,Login,Register , Dashboard , Logout,Vehicle_add,Complete_Profile,Qr_create,My_vehicle,Vehicle_detail,Scan_history,qr_scan_verfication,mark_qr_generated,delete_vehicle,notification,dismiss_notification,download_qr,mark_all_read
from django.urls import path ,include

urlpatterns = [
    path('jet',include('jet.urls','jet')),
    path('admin/', admin.site.urls),
    path('',Home,name="home"),
    path('register/',Register,name="register"),
    path('login/',Login,name="login"),
    path('dashboard/',Dashboard,name="dashboard"),
    path('logout/',Logout,name="logout"),
    path('accounts/', include('allauth.urls')),
    path('add_vehicle/',Vehicle_add,name="Vehicle_add"),
    path('profile/',Complete_Profile,name="complete_profile"),
    path('qr_management/',Qr_create,name="qr_create"),
    path('vehicle/',My_vehicle,name="my_vehicle"),
    path('vehicle/<uuid:qr_id>/',Vehicle_detail,name="vehicle_details"),
    path('scan_history/',Scan_history,name="scan_history"),
    path('qr/<uuid:qr_id>/',qr_scan_verfication,name="qr_scan_verifcation"),
    path('mark_qr_generated/<uuid:qr_id>/',mark_qr_generated,name="mark_qr_generated"),
    path('delete_vehicle/<uuid:qr_id>/',delete_vehicle,name="delete_vehicle"),
    path('notification',notification,name="notification"),
    path('dismiss_notification/<int:notification_id>/',dismiss_notification,name="dismiss_notification"),
    path('download_qr/<uuid:qr_id>/',download_qr,name="download_qr"),
    path('mark_all_read/',mark_all_read,name="mark_all_read"),
    path('password_reset/',auth_views.PasswordResetView.as_view(template_name="password_reset.html" ),name="password_reset"),
    path('password_reset_done/',auth_views.PasswordResetDoneView.as_view(template_name="password_reset_done.html"),name="password_reset_done"),
    path('reset/<uidb64>/<token>/',auth_views.PasswordResetConfirmView.as_view(template_name="password_reset_confirm.html"),name="password_reset_confirm"),
    path('reset_done',auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_complete.html"),name="password_reset_complete")
]
