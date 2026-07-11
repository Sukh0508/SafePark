"""
URL configuration for SafePark project.
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from main.views import (
    # Public / Auth
    Home, Login, Register, Logout,
    # Individual Dashboard
    Dashboard,
    # Vehicle
    Vehicle_add, My_vehicle, Vehicle_detail, edit_vehicle, delete_vehicle,
    # QR
    Qr_create, mark_qr_generated, download_qr,
    # Scan
    qr_scan_verfication, Scan_history,
    # Profile / Notifications
    Complete_Profile, notification, dismiss_notification, mark_all_read,
    # Invite
    join_society, join_society_guest,
    # Org Admin – core
    create_society, society_admin_dashboard,
    # Org Admin – sub-pages
    org_residents, org_vehicles, org_scan_reports,
    org_settings, org_pending_approvals, org_remove_member,
)

urlpatterns = [
    # ── Django Jet & Admin ─────────────────────────────────────────────────────
    path('jet', include('jet.urls', 'jet')),
    path('admin/', admin.site.urls),

    # ── Auth ───────────────────────────────────────────────────────────────────
    path('', Home, name='home'),
    path('register/', Register, name='register'),
    path('login/', Login, name='login'),
    path('logout/', Logout, name='logout'),
    path('accounts/', include('allauth.urls')),

    # ── Password Reset ─────────────────────────────────────────────────────────
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset.html'), name='password_reset'),
    path('password_reset_done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset_done', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'), name='password_reset_complete'),

    # ── Individual Dashboard ───────────────────────────────────────────────────
    path('dashboard/', Dashboard, name='dashboard'),

    # ── Vehicles ───────────────────────────────────────────────────────────────
    path('add_vehicle/', Vehicle_add, name='Vehicle_add'),
    path('vehicle/', My_vehicle, name='my_vehicle'),
    path('vehicle/<uuid:qr_id>/', Vehicle_detail, name='vehicle_details'),
    path('edit_vehicle/<uuid:qr_id>/', edit_vehicle, name='edit_vehicle'),
    path('delete_vehicle/<uuid:qr_id>/', delete_vehicle, name='delete_vehicle'),

    # ── QR ─────────────────────────────────────────────────────────────────────
    path('qr_management/', Qr_create, name='qr_create'),
    path('qr/<uuid:qr_id>/', qr_scan_verfication, name='qr_scan_verifcation'),
    path('mark_qr_generated/<uuid:qr_id>/', mark_qr_generated, name='mark_qr_generated'),
    path('download_qr/<uuid:qr_id>/', download_qr, name='download_qr'),

    # ── Scan History ───────────────────────────────────────────────────────────
    path('scan_history/', Scan_history, name='scan_history'),

    # ── Profile & Notifications ────────────────────────────────────────────────
    path('profile/', Complete_Profile, name='complete_profile'),
    path('notification', notification, name='notification'),
    path('dismiss_notification/<int:notification_id>/', dismiss_notification, name='dismiss_notification'),
    path('mark_all_read/', mark_all_read, name='mark_all_read'),

    # ── Invite / Join ──────────────────────────────────────────────────────────
    # Canonical invite link: /join/<code>/  (used in all invite links)
    path('join/<str:invite_code>/', join_society_guest, name='join_org'),
    # Legacy / alternate patterns kept for backward compatibility
    path('invite/<str:invite_code>/', join_society, name='join_society'),
    path('invite_guest/<str:invite_code>/', join_society_guest, name='join_society_guest'),
    path('join_society/', join_society, name='join_society_post'),

    # ── Org Admin: Create ─────────────────────────────────────────────────────
    path('create_society/', create_society, name='create_society'),

    # ── Org Admin: Dashboard ──────────────────────────────────────────────────
    path('society_admin/', society_admin_dashboard, name='society_admin_dashboard'),

    # ── Org Admin: Sub-pages ──────────────────────────────────────────────────
    path('org/residents/', org_residents, name='organization_residents'),
    path('org/vehicles/', org_vehicles, name='organization_vehicles'),
    path('org/scan-reports/', org_scan_reports, name='organization_scan_reports'),
    path('org/settings/', org_settings, name='organization_settings'),
    path('org/approvals/', org_pending_approvals, name='organization_pending'),
    path('org/remove-member/<int:profile_id>/', org_remove_member, name='org_remove_member'),
]
