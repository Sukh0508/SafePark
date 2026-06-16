from django import forms
from django.contrib.auth.models import User


class Registerform(forms.ModelForm):
    mobile = forms.CharField(max_length=15)
    password = forms.CharField(widget= forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username','email','password']
