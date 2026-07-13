from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from main.form import Registerform
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from main.models import Profile, Add_vehicle, Qr_scan_history, Notification, Society
from django.utils.timezone import localtime
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.db.models import Q, Count
from django.core.paginator import Paginator
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import uuid
import csv
from django.conf import settings
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from django.urls import reverse


# ─── Constants ────────────────────────────────────────────────────────────────

# Account types that classify an Organization Admin
ORG_ADMIN_TYPES = ["society", "hospital", "corporate", "education", "commercial"]


def _is_org_admin_type(account_type):
    """Return True if account_type belongs to an organization admin."""
    return account_type in ORG_ADMIN_TYPES


def _get_org_for_admin(user):
    """Return the Society managed by this user, or None."""
    return Society.objects.filter(admin=user).first()


def _require_org_admin(request):
    """
    Check that the current user is an org admin who has created an org.
    Returns (society, None) on success, or (None, redirect_response) on failure.
    """
    profile = get_object_or_404(Profile, user=request.user)
    if not _is_org_admin_type(profile.account_type):
        return None, HttpResponseForbidden("Access denied. You are not an organization admin.")
    society = _get_org_for_admin(request.user)
    if not society:
        messages.error(request, "You do not manage any organization.")
        return None, redirect("create_society")
    return society, None


# ─── Public Views ──────────────────────────────────────────────────────────────

def Home(request):
    return render(request, "index.html")


def Register(request):
    if request.method == "POST":
        form = Registerform(request.POST)
        account_type = request.POST.get("account_type")

        if form.is_valid():
            print("✅ FORM VALID")

            password = form.cleaned_data["password"]
            confirm_password = form.cleaned_data["confirm_password"]

            if password != confirm_password:
                form.add_error("confirm_password", "Passwords do not match")
                return render(request, "register.html", {
                    "form": form,
                    "is_invited": "pending_invite_code" in request.session,
                })

            # Create User
            user = form.save(commit=False)
            user.username = form.cleaned_data["email"]
            user.email = form.cleaned_data["email"]
            user.first_name = form.cleaned_data["username"]
            user.set_password(password)
            user.save()

            # Check if user came from an invite link
            pending_invite = request.session.pop("pending_invite_code", None)

            if pending_invite:
                organization = get_object_or_404(
                    Society,
                    invite_code=pending_invite
                )

                Profile.objects.create(
                    user=user,
                    mobile=form.cleaned_data["mobile"],
                    account_type="employee",
                    society=organization,
                )
            else:
                Profile.objects.create(
                    user=user,
                    mobile=form.cleaned_data["mobile"],
                    account_type=account_type,
                )

            return redirect("login")

        else:
            print("❌ FORM INVALID")
            print(form.errors)
            print(request.POST)

    else:
        form = Registerform()

    return render(request, "register.html", {
        "form": form,
        "is_invited": "pending_invite_code" in request.session,
    })

def Login(request):
    if request.method == "POST":
        username = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # If there's a pending invite in the session (user logged in via invite link)
            pending_invite = request.session.pop("pending_invite_code", None)
            if pending_invite:
                society = get_object_or_404(Society, invite_code=pending_invite)
                profile, _ = Profile.objects.get_or_create(user=user)
                profile.society = society
                # Only update account_type if it's not already an org admin type
                if not _is_org_admin_type(profile.account_type):
                    profile.account_type = "employee"
                profile.save()
                messages.success(request, f"You joined {society.name} successfully.")
            return redirect("dashboard")
        else:
            return render(request, "login.html", {
                "error": "Invalid username or password"
            })

    return render(request, "login.html")


def Logout(request):
    auth_logout(request)
    return redirect("home")


# ─── Individual Dashboard ──────────────────────────────────────────────────────

@login_required(login_url="/login/")
def Dashboard(request):
    profile = get_object_or_404(Profile, user=request.user)

    # ── Organization Admin: redirect to org dashboard or create page ──
    if _is_org_admin_type(profile.account_type):
        if Society.objects.filter(admin=request.user).exists():
            return redirect("society_admin_dashboard")
        else:
            return redirect("create_society")

    # ── Individual / Employee Dashboard ──────────────────────────────
    scans = Qr_scan_history.objects.filter(vehicle__user=request.user).order_by("-scaned_at")
    total_scan = scans.count()

    vehicles_with_qr = Add_vehicle.objects.filter(user=request.user, is_qr_generated=True)
    total_qr = vehicles_with_qr.count()

    all_vehicles = Add_vehicle.objects.filter(user=request.user)
    total_vehicles = all_vehicles.count()

    unread_notifications = Notification.objects.filter(
        user=request.user, is_read=False
    ).order_by("-created_at")
    notification_count = unread_notifications.count()

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")[:4]

    recent_scans = Qr_scan_history.objects.filter(
        vehicle__user=request.user
    ).order_by("-scaned_at")[:5]

    has_society = Society.objects.filter(admin=request.user).exists()

    response = render(request, "dashboard.html", {
        "total_scan": total_scan,
        "total_qr": total_qr,
        "total_vehicles": total_vehicles,
        "notification_count": notification_count,
        "notifications": notifications,
        "recent_scans": recent_scans,
        "is_org_admin": False,
        "has_society": has_society,
        "profile": profile,
    })
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


# ─── Vehicle Views ─────────────────────────────────────────────────────────────

@login_required
def Vehicle_add(request):
    if request.method == "POST":
        vehicle = Add_vehicle.objects.create(
            user=request.user,
            vehicle_number=request.POST.get("number"),
            vehicle_type=request.POST.get("vehicle_type"),
            brand=request.POST.get("brand"),
            model=request.POST.get("model"),
            year_of_manufacture=request.POST.get("manufacture"),
            vehicle_color_name=request.POST.get("color_name"),
            vehicle_color_code=request.POST.get("color_code"),
        )
        Notification.objects.create(
            user=vehicle.user,
            title="Vehicle Add Successfully",
            message=f"Your vehicle {vehicle.vehicle_number} was added.",
            notification_type="add",
        )
        return redirect("my_vehicle")

    notification_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()
    return render(request, "add_vehicle.html", {"notification_count": notification_count})


@login_required
def My_vehicle(request):
    query = request.GET.get("q")
    vehicles = Add_vehicle.objects.filter(user=request.user)
    total_vehicles = vehicles.count()

    if query:
        vehicles = vehicles.filter(
            Q(vehicle_number__icontains=query) |
            Q(brand__icontains=query) |
            Q(model__icontains=query) |
            Q(vehicle_type__icontains=query)
        )

    notification_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    return render(request, "vehicle.html", {
        "vehicles": vehicles,
        "total_vehicles": total_vehicles,
        "notification_count": notification_count,
    })


def Vehicle_detail(request, qr_id):
    vehicle = get_object_or_404(Add_vehicle, qr_id=qr_id)
    profile = Profile.objects.get(user=vehicle.user)

    visible_fields = {
        "name": profile.show_name,
        "city": profile.show_city,
        "mobile": profile.show_mobile,
        "email": profile.show_email,
        "society": profile.show_society,
    }

    return render(request, "vehicel_detail.html", {
        "vehicle": vehicle,
        "profile": profile,
        "visible_fields": visible_fields,
    })


@login_required
def edit_vehicle(request, qr_id):
    vehicle = get_object_or_404(Add_vehicle, qr_id=qr_id, user=request.user)
    if request.method == "POST":
        vehicle.brand = request.POST.get("brand", vehicle.brand)
        vehicle.model = request.POST.get("model", vehicle.model)
        vehicle.vehicle_color_name = request.POST.get("color_name", vehicle.vehicle_color_name)
        vehicle.vehicle_color_code = request.POST.get("color_code", vehicle.vehicle_color_code)
        vehicle.year_of_manufacture = request.POST.get("manufacture", vehicle.year_of_manufacture)
        vehicle.save()
        messages.success(request, "Vehicle updated successfully.")
        return redirect("my_vehicle")

    return render(request, "edit_vehicle.html", {"vehicle": vehicle})


@login_required
def delete_vehicle(request, qr_id):
    vehicle = get_object_or_404(Add_vehicle, qr_id=qr_id)
    
    # Security check
    is_owner = (vehicle.user == request.user)
    is_admin = False
    if not is_owner:
        try:
            admin_society = Society.objects.get(admin=request.user)
            if vehicle.user.profile.society == admin_society:
                is_admin = True
        except Society.DoesNotExist:
            pass
            
    if not is_owner and not is_admin:
        return HttpResponseForbidden("You are not authorized to delete this vehicle.")

    Notification.objects.create(
        user=vehicle.user,
        title="Vehicle Deleted",
        message=f"Vehicle {vehicle.vehicle_number} was deleted.",
        notification_type="delete",
    )
    vehicle.delete()
    
    # Redirect based on who deleted it
    if is_admin and request.GET.get('next') == 'org':
        return redirect("organization_vehicles")
    return redirect("my_vehicle")


# ─── QR Views ─────────────────────────────────────────────────────────────────

@login_required
def Qr_create(request):
    vehicles = Add_vehicle.objects.filter(user=request.user)
    total_qr = Add_vehicle.objects.filter(user=request.user, is_qr_generated=True).count()
    notification_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()
    return render(request, "qr_management.html", {
        "vehicles": vehicles,
        "total_qr": total_qr,
        "notification_count": notification_count,
    })


@login_required
def mark_qr_generated(request, qr_id):
    vehicle = Add_vehicle.objects.get(user=request.user, qr_id=qr_id)
    vehicle.is_qr_generated = True
    vehicle.save()
    return JsonResponse({"status": True})


def qr_scan_verfication(request, qr_id):
    vehicle = get_object_or_404(Add_vehicle, qr_id=qr_id)

    if request.method == "POST":
        scanner_name = request.POST.get("scanner_name", "").strip()
        scanner_mobile = request.POST.get("scanner_mobile", "").strip()
        scanner_email = request.POST.get("scanner_email", "").strip()
        purpose = request.POST.get("purpose", "").strip()

        if not scanner_name or not scanner_mobile or not purpose:
            return render(request, "Qr_scan_verifcation.html", {
                "vehicle": vehicle,
                "error": "All fields are required",
            })

        # Prevent spam scan within 5 seconds from same mobile
        last_scan = Qr_scan_history.objects.filter(
            vehicle=vehicle, scanner_mobile=scanner_mobile
        ).order_by("-scaned_at").first()

        if last_scan:
            diff = (timezone.now() - last_scan.scaned_at).seconds
            if diff < 5:
                return redirect("vehicle_details", qr_id=vehicle.qr_id)

        Qr_scan_history.objects.create(
            vehicle=vehicle,
            scanner_name=scanner_name,
            scanner_mobile=scanner_mobile,
            scanner_email=scanner_email,
            purpose=purpose,
        )
        Notification.objects.create(
            user=vehicle.user,
            title="Vehicle QR Scanned",
            message=f"{scanner_name} scanned your vehicle at {timezone.localtime(timezone.now()).strftime('%I:%M %p')}.",
            notification_type="scan",
        )
        return redirect("vehicle_details", qr_id=vehicle.qr_id)

    return render(request, "Qr_scan_verifcation.html", {"vehicle": vehicle})


@login_required
def download_qr(request, qr_id):
    vehicle = get_object_or_404(Add_vehicle, qr_id=qr_id)

    # Security check: owner OR org admin
    if vehicle.user != request.user:
        try:
            admin_society = Society.objects.get(admin=request.user)
            if not hasattr(vehicle.user, 'profile') or vehicle.user.profile.society != admin_society:
                return HttpResponseForbidden("You are not authorized to download this QR.")
        except Society.DoesNotExist:
            return HttpResponseForbidden("You are not authorized to download this QR.")

    if not vehicle.is_qr_generated:
        vehicle.is_qr_generated = True
        vehicle.save()

    response = HttpResponse(content_type="application/pdf")
    disposition = "inline" if request.GET.get("print") == "1" else "attachment"
    response["Content-Disposition"] = f'{disposition}; filename="SafePark-{vehicle.vehicle_number}.pdf"'

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle(f"SafePark QR Sticker - {vehicle.vehicle_number}")

    width, height = A4
    royal_blue = HexColor("#1E3A8A")
    white = HexColor("#FFFFFF")
    text_dark = HexColor("#1F2937")
    text_muted = HexColor("#6B7280")
    
    # Card dimensions
    card_w = 380
    card_h = 540
    card_x = (width - card_w) / 2
    card_y = (height - card_h) / 2

    # Draw premium shadow (offset light gray rect)
    pdf.setFillColor(HexColor("#E5E7EB"))
    pdf.roundRect(card_x + 8, card_y - 8, card_w, card_h, 15, fill=1, stroke=0)
    
    # Draw card background
    pdf.setFillColor(white)
    pdf.setStrokeColor(HexColor("#D1D5DB"))
    pdf.setLineWidth(1)
    pdf.roundRect(card_x, card_y, card_w, card_h, 15, fill=1, stroke=1)

    # Banner (Top part of card)
    banner_y = card_y + card_h - 110
    pdf.setFillColor(royal_blue)
    p = pdf.beginPath()
    p.moveTo(card_x, banner_y)
    p.lineTo(card_x, card_y + card_h - 15)
    p.arcTo(card_x, card_y + card_h - 30, card_x + 30, card_y + card_h, 180, -90)
    p.lineTo(card_x + card_w - 15, card_y + card_h)
    p.arcTo(card_x + card_w - 30, card_y + card_h - 30, card_x + card_w, card_y + card_h, 90, -90)
    p.lineTo(card_x + card_w, banner_y)
    p.close()
    pdf.drawPath(p, fill=1, stroke=0)

    # Header Text
    pdf.setFillColor(white)
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawCentredString(width / 2, banner_y + 45, "SAFEPARK")
    pdf.setFont("Helvetica", 15)
    pdf.drawCentredString(width / 2, banner_y + 20, "Vehicle Safety QR")

    # Center QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=2,
    )
    qr_url = request.build_absolute_uri(reverse("qr_scan_verifcation", args=[vehicle.qr_id]))
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white").convert("RGB")
    
    temp_path = os.path.join(settings.BASE_DIR, "tmp_qr.png")
    qr_img.save(temp_path)
    
    qr_size = 200
    qr_x = (width - qr_size) / 2
    qr_y = banner_y - 30 - qr_size
    pdf.drawImage(temp_path, qr_x, qr_y, width=qr_size, height=qr_size)
    os.remove(temp_path)

    # Below QR Details
    details_y = qr_y - 45
    pdf.setFillColor(royal_blue)
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawCentredString(width / 2, details_y, vehicle.vehicle_number.upper())
    
    details_y -= 28
    pdf.setFillColor(text_dark)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, details_y, f"{vehicle.brand} {vehicle.model} - {vehicle.get_vehicle_type_display()}")
    
    details_y -= 24
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(width / 2, details_y, f"Owner: {vehicle.user.first_name or vehicle.user.email}")
    
    # Organization Info
    society = getattr(vehicle.user.profile, 'society', None)
    if society:
        details_y -= 45
        pdf.setFillColor(text_muted)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, details_y, f"{society.get_organization_type_display().upper()}")
        details_y -= 22
        pdf.setFillColor(royal_blue)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawCentredString(width / 2, details_y, society.name)

    # Footer
    footer_y = card_y + 25
    pdf.setFillColor(text_muted)
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, footer_y, "Protected by SafePark | Emergency Contact Available")

    pdf.showPage()
    pdf.save()

    pdf_data = buffer.getvalue()
    buffer.close()
    response.write(pdf_data)
    return response


# ─── Scan History (Individual) ─────────────────────────────────────────────────

@login_required(login_url="/login/")
def Scan_history(request):
    scans = Qr_scan_history.objects.filter(
        vehicle__user=request.user
    ).order_by("-scaned_at")
    total_scan = scans.count()

    notification_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    return render(request, "scan_history.html", {
        "scans": scans,
        "total_scan": total_scan,
        "notification_count": notification_count,
    })


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def Complete_Profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.address = request.POST.get("address")
        profile.mobile = request.POST.get("mobile")
        profile.city = request.POST.get("city")
        profile.state = request.POST.get("state")
        profile.society_name = request.POST.get("society_name")
        profile.account_type = request.POST.get("account_type")
        profile.emergency_contact_name = request.POST.get("emergency_contact_name")
        profile.emergency_conatct_number = request.POST.get("emergency_conatct_number")
        profile.show_name = "show_name" in request.POST
        profile.show_city = "show_city" in request.POST
        profile.show_mobile = "show_mobile" in request.POST
        profile.show_email = "show_email" in request.POST
        profile.show_society = "show_society" in request.POST
        profile.save()
        return redirect("dashboard")

    notification_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()
    is_org_admin = _is_org_admin_type(profile.account_type or "")
    has_society = Society.objects.filter(admin=request.user).exists()

    return render(request, "profile.html", {
        "profile": profile,
        "notification_count": notification_count,
        "is_org_admin": is_org_admin,
        "has_society": has_society,
    })


# ─── Notifications ────────────────────────────────────────────────────────────

@login_required
def notification(request):
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")
    return render(request, "notifications.html", {"notifications": notifications})


@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notification")


@login_required
def dismiss_notification(request, notification_id):
    notif = get_object_or_404(Notification, id=notification_id, user=request.user)
    notif.is_read = True
    notif.save()
    return redirect("notification")


# ─── Invite / Join Views ───────────────────────────────────────────────────────

def join_society(request, invite_code=None):
    """Handle both GET (with invite_code in URL) and POST (with invite_code in form)."""
    if request.method == "POST":
        invite_code = request.POST.get("invite_code") or invite_code

    if not invite_code:
        messages.error(request, "Please provide a valid invite code.")
        return redirect("complete_profile")

    if not request.user.is_authenticated:
        request.session["pending_invite_code"] = invite_code
        return redirect("register")

    society = get_object_or_404(Society, invite_code=invite_code)
    profile, created = Profile.objects.get_or_create(user=request.user)
    profile.society = society
    # Only assign employee type if they are not already an org admin
    if not _is_org_admin_type(profile.account_type or ""):
        profile.account_type = "employee"
    profile.save()
    messages.success(request, f"You joined {society.name} successfully.")
    return redirect("dashboard")


def join_society_guest(request, invite_code):
    """Save invite code to session and redirect to register (for unauthenticated users)."""
    request.session["pending_invite_code"] = invite_code
    return redirect("register")


# ─── Create Organization ───────────────────────────────────────────────────────

@login_required
def create_society(request):
    profile = get_object_or_404(Profile, user=request.user)

    if not _is_org_admin_type(profile.account_type or ""):
        messages.error(request, "Only organization admins can create an organization.")
        return redirect("dashboard")

    # Prevent duplicate organization
    existing = Society.objects.filter(admin=request.user).first()
    if existing:
        profile.society = existing
        profile.save()
        return redirect("society_admin_dashboard")

    if request.method == "POST":
        org_name = request.POST.get("name", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()

        if not org_name:
            messages.error(request, "Organization name is required.")
            return render(request, "create_society.html", {"profile": profile})

        society = Society.objects.create(
            name=org_name,
            city=city,
            state=state,
            organization_type=profile.account_type,
            admin=request.user,
        )
        profile.society = society
        profile.save()
        messages.success(request, "Organization created successfully!")
        return redirect("society_admin_dashboard")

    return render(request, "create_society.html", {"profile": profile})


# ─── Organization Admin Dashboard ─────────────────────────────────────────────

@login_required
def society_admin_dashboard(request):
    society, err = _require_org_admin(request)
    if err:
        return err

    # Ensure admin's own profile is linked to the society
    profile = get_object_or_404(Profile, user=request.user)
    if profile.society != society:
        profile.society = society
        profile.save()

    # ── Stats ──────────────────────────────────────────────────────────
    members = Profile.objects.filter(society=society)
    total_members = members.count()

    # All vehicles belonging to org members (by society FK)
    org_vehicles = Add_vehicle.objects.filter(user__profile__society=society)
    total_vehicles = org_vehicles.count()
    total_qr = org_vehicles.filter(is_qr_generated=True).count()

    # All QR scans for org vehicles
    org_scans = Qr_scan_history.objects.filter(vehicle__user__profile__society=society)
    total_scans = org_scans.count()

    # ── Recent data ────────────────────────────────────────────────────
    recent_members = members.order_by("-user__date_joined")[:5]
    recent_vehicles = org_vehicles.order_by("-id")[:5]
    recent_scans = org_scans.order_by("-scaned_at")[:5]

    invite_link = request.build_absolute_uri(
        reverse("join_org", args=[society.invite_code])
    )

    return render(request, "society_admin.html", {
        "society": society,
        "total_members": total_members,
        "total_vehicles": total_vehicles,
        "total_qr": total_qr,
        "total_scans": total_scans,
        "recent_members": recent_members,
        "recent_vehicles": recent_vehicles,
        "recent_scans": recent_scans,
        "invite_link": invite_link,
        "active_page": "dashboard",
    })


# ─── Org Residents ────────────────────────────────────────────────────────────

@login_required
def org_residents(request):
    society, err = _require_org_admin(request)
    if err:
        return err

    query = request.GET.get("q", "").strip()
    members_qs = Profile.objects.filter(society=society).select_related("user")

    if query:
        members_qs = members_qs.filter(
            Q(user__first_name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(mobile__icontains=query) |
            Q(city__icontains=query)
        )

    # Annotate each profile with their vehicle count
    members_qs = members_qs.annotate(vehicle_count=Count("user__add_vehicle"))

    paginator = Paginator(members_qs, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    invite_link = request.build_absolute_uri(
        reverse("join_org", args=[society.invite_code])
    )

    return render(request, "org_residents.html", {
        "society": society,
        "page_obj": page_obj,
        "query": query,
        "invite_link": invite_link,
        "total_members": Profile.objects.filter(society=society).count(),
        "active_page": "residents",
    })


# ─── Org Vehicles ─────────────────────────────────────────────────────────────

@login_required
def org_vehicles(request):
    society, err = _require_org_admin(request)
    if err:
        return err

    query = request.GET.get("q", "").strip()
    vehicle_type_filter = request.GET.get("type", "").strip()

    vehicles_qs = Add_vehicle.objects.filter(
        user__profile__society=society
    ).select_related("user", "user__profile")

    if query:
        vehicles_qs = vehicles_qs.filter(
            Q(vehicle_number__icontains=query) |
            Q(brand__icontains=query) |
            Q(model__icontains=query) |
            Q(user__first_name__icontains=query)
        )

    if vehicle_type_filter:
        vehicles_qs = vehicles_qs.filter(vehicle_type=vehicle_type_filter)

    paginator = Paginator(vehicles_qs, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    vehicle_types = Add_vehicle.VEHICLE_TYPE

    invite_link = request.build_absolute_uri(
        reverse("join_org", args=[society.invite_code])
    )

    return render(request, "org_vehicles.html", {
        "society": society,
        "page_obj": page_obj,
        "query": query,
        "vehicle_type_filter": vehicle_type_filter,
        "vehicle_types": vehicle_types,
        "invite_link": invite_link,
        "total_vehicles": Add_vehicle.objects.filter(user__profile__society=society).count(),
        "active_page": "vehicles",
    })


# ─── Org Scan Reports ─────────────────────────────────────────────────────────

@login_required
def org_scan_reports(request):
    society, err = _require_org_admin(request)
    if err:
        return err

    query = request.GET.get("q", "").strip()
    start_date = request.GET.get("start_date", "").strip()
    end_date = request.GET.get("end_date", "").strip()
    
    scans_qs = Qr_scan_history.objects.filter(
        vehicle__user__profile__society=society
    ).select_related("vehicle", "vehicle__user").order_by("-scaned_at")

    if query:
        scans_qs = scans_qs.filter(
            Q(scanner_name__icontains=query) |
            Q(scanner_mobile__icontains=query) |
            Q(purpose__icontains=query) |
            Q(vehicle__vehicle_number__icontains=query) |
            Q(vehicle__user__first_name__icontains=query)
        )
        
    if start_date:
        scans_qs = scans_qs.filter(scaned_at__date__gte=start_date)
    if end_date:
        scans_qs = scans_qs.filter(scaned_at__date__lte=end_date)

    # ── CSV Export ─────────────────────────────────────────────────────
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{society.name}-scan-report.csv"'
        writer = csv.writer(response)
        writer.writerow(["Vehicle", "Owner", "Scanner Name", "Scanner Mobile", "Purpose", "Date"])
        for scan in scans_qs:
            writer.writerow([
                scan.vehicle.vehicle_number,
                scan.vehicle.user.get_full_name() or scan.vehicle.user.first_name,
                scan.scanner_name,
                scan.scanner_mobile,
                scan.purpose,
                localtime(scan.scaned_at).strftime("%d %b %Y %I:%M %p"),
            ])
        return response

    paginator = Paginator(scans_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    invite_link = request.build_absolute_uri(
        reverse("join_org", args=[society.invite_code])
    )

    return render(request, "org_scan_reports.html", {
        "society": society,
        "page_obj": page_obj,
        "query": query,
        "start_date": start_date,
        "end_date": end_date,
        "total_scans": Qr_scan_history.objects.filter(vehicle__user__profile__society=society).count(),
        "invite_link": invite_link,
        "active_page": "reports",
    })


# ─── Org Pending Approvals ────────────────────────────────────────────────────

@login_required
def org_pending_approvals(request):
    society, err = _require_org_admin(request)
    if err:
        return err

    # Currently shows all members — approval workflow is future-ready
    members = Profile.objects.filter(society=society).select_related("user").order_by(
        "-user__date_joined"
    )

    invite_link = request.build_absolute_uri(
        reverse("join_org", args=[society.invite_code])
    )

    return render(request, "org_pending_approvals.html", {
        "society": society,
        "members": members,
        "invite_link": invite_link,
        "total_members": members.count(),
        "active_page": "approvals",
    })


# ─── Org Settings ─────────────────────────────────────────────────────────────

@login_required
def org_settings(request):
    society, err = _require_org_admin(request)
    if err:
        return err

    invite_link = request.build_absolute_uri(
        reverse("join_org", args=[society.invite_code])
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update":
            # ── Update org details ─────────────────────────────────────
            new_name = request.POST.get("name", "").strip()
            if not new_name:
                messages.error(request, "Organization name cannot be empty.")
            else:
                society.name = new_name
                society.city = request.POST.get("city", "").strip()
                society.state = request.POST.get("state", "").strip()
                society.organization_type = request.POST.get("organization_type", society.organization_type)
        if form.is_valid():
            form.save()
            messages.success(request, "Organization settings updated.")
            return redirect("organization_settings")

        elif action == "regenerate":
            # ── Regenerate invite code ─────────────────────────────────
            society.invite_code = uuid.uuid4().hex[:8].upper()
            society.save()
            messages.success(request, f"New invite code generated: {society.invite_code}")
            return redirect("organization_settings")

        elif action == "delete":
            # ── Delete organization ────────────────────────────────────
            # Detach all members first
            Profile.objects.filter(society=society).update(society=None)
            society.delete()
            messages.success(request, "Organization deleted successfully.")
            return redirect("create_society")

    return render(request, "org_settings.html", {
        "society": society,
        "invite_link": invite_link,
        "org_types": Society.ORGANIZATION_TYPES,
        "active_page": "settings",
    })


# ─── Org Member Removal ───────────────────────────────────────────────────────

@login_required
def org_remove_member(request, profile_id):
    society, err = _require_org_admin(request)
    if err:
        return err

    member_profile = get_object_or_404(Profile, id=profile_id, society=society)

    # Prevent removing self
    if member_profile.user == request.user:
        messages.error(request, "You cannot remove yourself from the organization.")
        return redirect("organization_residents")

    if request.method == "POST":
        member_profile.society = None
        member_profile.save()
        messages.success(request, f"{member_profile.user.get_full_name() or member_profile.user.email} has been removed.")
        return redirect("organization_residents")