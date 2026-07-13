from django import forms
from django.contrib.auth.models import User


class Registerform(forms.ModelForm):
    full_name = forms.CharField(max_length=150, required=True, label="Full Name")
    mobile = forms.CharField(max_length=15)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email
