from django import forms

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=30)
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    password1 = forms.PasswordInput()
    password2 = forms.PasswordInput()
    email_address = forms.EmailField()
