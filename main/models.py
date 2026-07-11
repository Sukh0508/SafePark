from django.db import models
from django.contrib.auth.models import User
import uuid


class Society(models.Model):
    ORGANIZATION_TYPES = [
    ("society", "Society"),
    ("hospital", "Hospital"),
    ("corporate", "Corporate"),
    ("education", "Educational Campus"),
    ("commercial", "Commercial Complex"),
]
    name = models.CharField(max_length=150)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    invite_code = models.CharField(max_length=12, unique=True, blank=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_societies')
    created_at = models.DateTimeField(auto_now_add=True)
    organization_type = models.CharField(
    max_length=20,
    choices=ORGANIZATION_TYPES
)

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15)

    address = models.TextField(blank=True , null=True)
    city = models.CharField(max_length=100 , blank=True ,null=True) 
    state = models.CharField(max_length=100 , blank=True,null=True)
    society_name = models.CharField(max_length=100, blank=True , null=True)

    emergency_contact_name = models.CharField(max_length=100, blank=True,null= True)
    emergency_conatct_number = models.CharField(max_length=15 ,null=True)
    society = models.ForeignKey(Society, on_delete=models.SET_NULL, null=True, blank=True, related_name='residents')

    account_type = models.CharField(
    max_length=20,
    blank=True,
    null=True
)

    # privacy Settings
    show_name = models.BooleanField(default=True ,null=True)
    show_city = models.BooleanField(default=False,null=True)
    show_mobile = models.BooleanField(default=False,null=True)
    show_email = models.BooleanField(default=False,null=True)
    show_society = models.BooleanField(default=False,null=True)
    
    def __str__(self):
        return self.user.username
    

class Add_vehicle(models.Model):
    VEHICLE_TYPE = [
         ("Car","Car"),
         ("Motorcycle / Bike","Motorcycle / Bike"),
         ("SUV","SUV"),
         ("Truck","Truck"),
         ("Van","Van"),
         ("EV","EV")
    ]
    BRAND = [
        ("Toyota","Toyota"),
        ("Honda","Honda"),
        ("Tata","Tata"),
        ("Maruti Suzuki","Maruti Suzuki"),
        ("Hyundai","Hyundai"),
        ("Mahindra","Mahindra"),
        ("Royal Enfield","Royal Enfield")
]
    user = models.ForeignKey(User,on_delete=models.CASCADE)

    vehicle_number = models.CharField(max_length=100)
    vehicle_type = models.CharField(max_length=50,choices=VEHICLE_TYPE)
    brand = models.CharField(max_length=50,choices=BRAND)
    model = models.CharField(max_length=50)
    year_of_manufacture = models.PositiveIntegerField()
    vehicle_color_name = models.CharField(max_length=50)
    vehicle_color_code = models.CharField(max_length=20)

    qr_id = models.UUIDField(default=uuid.uuid4,editable=False,unique=True)
    is_qr_generated = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}"
    
class Qr_scan_history(models.Model):
    vehicle = models.ForeignKey(Add_vehicle,on_delete=models.CASCADE)

    scanner_name = models.CharField(max_length=100, blank=True)
    scanner_mobile = models.CharField(max_length=20, blank=True)
    scanner_email = models.EmailField(blank=True, null=True)
    purpose = models.CharField(max_length=100, blank=True)
    scaned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.scanner_name
    

class Notification(models.Model):
    NOTIFICATION_TYPES = [
    ("scan", "QR Scan"),
    ("add", "Vehicle Added"),
    ("delete", "Vehicle Deleted"),
]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    message = models.CharField(max_length=100)

    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title





