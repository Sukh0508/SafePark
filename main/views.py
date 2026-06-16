from django.shortcuts import render ,redirect ,get_object_or_404
from django.contrib.auth.decorators import login_required
from main.form import Registerform
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout
from main.models import Profile , Add_vehicle , Qr_scan_history , Notification
from django.utils.timezone import localtime
from django.utils import timezone
from django.http import JsonResponse , HttpResponse
from django.db.models import Q
import qrcode

# from django.http import HttpResponse

# Create your views here.


def Home(request):
    #  return HttpResponse("Working")
    return render( request ,"index.html")
def Register(request):

    if request.method == "POST":
        form = Registerform(request.POST)

        if form.is_valid():
          password = form.cleaned_data["password"]
          confirm_password = form.cleaned_data["confirm_password"]

          if password != confirm_password:
               form.add_error("confirm_password", "Passwords do not match")
               return render(request, "register.html", {"form": form})
              
          
          user = form.save(commit=False)

          user.username = form.cleaned_data["email"]
          user.email = form.cleaned_data["email"]
          user.first_name = form.cleaned_data["username"]
          
          user.set_password(form.cleaned_data["password"])
          user.save()
  
          Profile.objects.create(
              user = user,
              mobile = form.cleaned_data["mobile"]

          )
          return redirect("login")
        
    else:
            form = Registerform()
    #  return HttpResponse("Working")
    return render( request ,"register.html",{
        "form":form
    })

def Login(request):
    if request.method == "POST":
        username = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request , username=username , password = password)
        print(user)

        if user is not None:
            login(request , user)
            return redirect("dashboard")
        else:
            return render(request,"login.html",{
                "error": "Invalid username or password"
            })
    
    return render(request,"login.html")

@login_required(login_url='/login/')
def Dashboard(request):
    scans = Qr_scan_history.objects.filter(
        vehicle__user=request.user
    ).order_by("-scaned_at")
    total_scan = scans.count()
    
    vehicles = Add_vehicle.objects.filter(user=request.user,is_qr_generated = True)
    total_qr = vehicles.count()

    vehicles = Add_vehicle.objects.filter(user=request.user)
    total_vehicles = vehicles.count()
    response = render(request, "dashboard.html")

    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    # return response

    notifications = Notification.objects.filter(
    user=request.user,
    is_read=False
   ).order_by("-created_at")
    

    notification_count = notifications.count()

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:4]


    return render(request,"dashboard.html",{
    "total_scan":total_scan,
    "total_qr": total_qr,
    "total_vehicles":total_vehicles,
    "notification_count": notification_count,
    "notifications":notifications

   })

def Logout(request):
    auth_logout(request)
    return redirect('home')

def Vehicle_add(request):
    if request.method == "POST":
       print(request.user)
       vehicle = Add_vehicle.objects.create(
        user = request.user,   
        vehicle_number = request.POST.get("number"),
        vehicle_type = request.POST.get("vehicle_type"),
        brand = request.POST.get("brand"),
        model = request.POST.get("model"),
        year_of_manufacture = request.POST.get("manufacture"),
        vehicle_color_name  = request.POST.get("color_name"),
        vehicle_color_code  = request.POST.get("color_code"),
      )
       print(request.POST.get("color_code"))
       Notification.objects.create(
        user= vehicle.user,
        title="Vehicle Add Successfully",
        message=f"Your vehicle {vehicle.vehicle_number} was added .",
        notification_type="add"
        )
    #    print("TYPE =", request.POST.get("type"))
    #    print("POST =", request.POST)
    #    print("Vehicle Saved")
       return redirect("my_vehicle")

    return render(request,"add_vehicle.html")

@login_required
def Complete_Profile(request):
    profile, created = Profile.objects.get_or_create(
        user = request.user
    )
    if request.method == "POST":
        profile.address = request.POST.get("address")
        profile.mobile = request.POST.get("mobile")
        profile.city = request.POST.get("city")
        profile.state = request.POST.get("state")
        profile.society_name = request.POST.get("society_name")

        profile.emergency_contact_name = request.POST.get("emergency_contact_name")
        profile.emergency_conatct_number = request.POST.get("emergency_conatct_number")

        profile.show_name = "show_name" in request.POST
        profile.show_city = "show_city" in request.POST
        profile.show_mobile = "show_mobile" in request.POST
        profile.show_email = "show_email" in request.POST

        profile.save()

        
       

        return redirect("dashboard")
    
    notifications = Notification.objects.filter(
    user=request.user,
    is_read=False
    ).order_by("-created_at")

    notification_count = notifications.count()

    return render(request,"profile.html",{
        "profile":profile,
        "notification_count": notification_count
    })
def Qr_create(request):
    vehicles = Add_vehicle.objects.filter(user=request.user)
    # Count only vehicles for which a QR has been generated
    total_qr = Add_vehicle.objects.filter(user=request.user, is_qr_generated=True).count()

    notifications = Notification.objects.filter(
    user=request.user,
    is_read=False
   ).order_by("-created_at")

    notification_count = notifications.count()

    return render(request, "qr_management.html", {
        "vehicles": vehicles,
        "total_qr":total_qr,
         "notification_count": notification_count
    })

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
    notifications = Notification.objects.filter(
    user=request.user,
    is_read=False
   ).order_by("-created_at")

    notification_count = notifications.count()
    # print("USER =", request.user)
    # print("COUNT =", vehicle.count())
    return render(request,"vehicle.html",{
        "vehicles":vehicles,
        "total_vehicles":total_vehicles,
        "notification_count": notification_count
    })

def Vehicle_detail(request ,qr_id):

    print("VEHICLE DETAIL HIT")
    vehicle = get_object_or_404(Add_vehicle,qr_id=qr_id)

  
    profile = Profile.objects.get(user=vehicle.user)
   
    return render(request,"vehicel_detail.html",{
        "vehicle":vehicle,
        "profile": profile
    })
  
@login_required(login_url='/login/')
def Scan_history(request):
    scans = Qr_scan_history.objects.filter(
        vehicle__user=request.user
    ).order_by("-scaned_at")
    total_scan = scans.count()

    notifications = Notification.objects.filter(
    user=request.user,
    is_read=False
   ).order_by("-created_at")
    notification_count = notifications.count()


    return render(request,"scan_history.html",{
        "scans":scans,
        "total_scan":total_scan,
        "notification_count": notification_count
    })

def qr_scan_verfication(request, qr_id):
    vehicle = get_object_or_404(Add_vehicle, qr_id=qr_id)

    if request.method == "POST":

        scanner_name = request.POST.get("scanner_name", "").strip()
        scanner_mobile = request.POST.get("scanner_mobile", "").strip()
        purpose = request.POST.get("purpose", "").strip()

        # ❌ BLOCK EMPTY DATA
        if not scanner_name or not scanner_mobile or not purpose:
            return render(request, "Qr_scan_verifcation.html", {
                "vehicle": vehicle,
                "error": "All fields are required"
            })

        # 🔥 PREVENT DUPLICATE (5 sec rule)
        last_scan = Qr_scan_history.objects.filter(
            vehicle=vehicle,
            scanner_mobile=scanner_mobile
        ).order_by("-scaned_at").first()

        if last_scan:
            from django.utils import timezone
            diff = (timezone.now() - last_scan.scaned_at).seconds

            if diff < 5:
                return redirect("vehicle_details", qr_id=vehicle.qr_id)

        # ✅ SAVE SCAN
        Qr_scan_history.objects.create(
            vehicle=vehicle,
            scanner_name=scanner_name,
            scanner_mobile=scanner_mobile,
            purpose=purpose
        )
        Notification.objects.create(
             user=vehicle.user,
             title="QR Code Scanned",
             message=f"Your vehicle {vehicle.vehicle_number} QR was scanned.",
             notification_type="scan"
        )
        

        return redirect("vehicle_details", qr_id=vehicle.qr_id)

    return render(request, "Qr_scan_verifcation.html", {
        "vehicle": vehicle
    })

def mark_qr_generated(request,qr_id):
 
    vehicle = Add_vehicle.objects.get(
        user = request.user,
        qr_id = qr_id

    )
    vehicle.is_qr_generated = True
    vehicle.save()
    
    return JsonResponse({"status":True})



def delete_vehicle(request, qr_id):
    vehicle = get_object_or_404(
        Add_vehicle,
        qr_id=qr_id
    )
    Notification.objects.create(
        user= vehicle.user,
        title="Vehicle Deleted Successfully",
        message=f"Your vehicle {vehicle.vehicle_number} was deleted .",
        notification_type="delete"
    )

    vehicle.delete()

    return redirect("my_vehicle")


def notification(request):
    notifications = Notification.objects.filter(
        user= request.user
    ).order_by("-created_at")

    
    return render(request,"notifications.html",{
        "notifications":notifications
    })

def mark_all_read(request):
    Notification.objects.filter(
        user = request.user,
        is_read = False
    ).update(is_read= True)

    return redirect('notification')

def dismiss_notification(request,notification_id):
    notification = get_object_or_404(
        Notification,
        id = notification_id,
        user= request.user,
    )
    notification.is_read = True
    notification.save()

    return redirect('notification')

def download_qr(request,qr_id):
    vehicle = get_object_or_404(
        Add_vehicle,
        qr_id = qr_id
    )
    # Mark QR as generated when user downloads the QR image
    if not vehicle.is_qr_generated:
        vehicle.is_qr_generated = True
        vehicle.save()
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=4,

    )
    qr.add_data(
        f"https://safepark-clp8.onrender.com/qr/{vehicle.qr_id}/"
    )
    qr.make(fit=True)

    img = qr.make_image(
        fill_color ="black",
        back_color = "white"
    )
    response = HttpResponse(content_type="image/png")

    response['Content-Disposition'] = (
        f'attachment; filename="SafePark-QR.png"'
    )

    img.save(response, "PNG")

    return response

# def password_reset(request):
#     return render(request,"password_reset.html")