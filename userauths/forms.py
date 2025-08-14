from django import forms
from django.contrib.auth.forms import UserCreationForm
from userauths.models import User, Profile


# class UserRegisterForm(UserCreationForm):
#     username = forms.CharField(
#         widget=forms.TextInput(
#             attrs={
#                 "placeholder": "Username",
#                 "class": "form-control",
#                 "required": "required",
#             }
#         )
#     )
#     email = forms.EmailField(
#         widget=forms.EmailInput(
#             attrs={
#                 "placeholder": "Email Address",
#                 "class": "form-control",
#                 "required": "required",
#             }
#         )
#     )
#     password1 = forms.CharField(
#         widget=forms.PasswordInput(
#             attrs={
#                 "placeholder": "Password",
#                 "class": "form-control",
#                 "required": "required",
#             }
#         )
#     )
#     password2 = forms.CharField(
#         widget=forms.PasswordInput(
#             attrs={
#                 "placeholder": "Confirm Password",
#                 "class": "form-control",
#                 "required": "required",
#             }
#         )
#     )

#     class Meta:
#         model = User
#         fields = ["username", "email"]

#     def clean_email(self):
#         email = self.cleaned_data.get("email")
#         if User.objects.filter(email=email).exists():
#             raise forms.ValidationError("Email này đã được sử dụng.")
#         return email

#     def clean_username(self):
#         username = self.cleaned_data.get("username")
#         if User.objects.filter(username=username).exists():
#             raise forms.ValidationError("Username này đã được sử dụng.")
#         return username


from django import forms
from django.contrib.auth.forms import UserCreationForm
from userauths.models import User, Profile
from core.models import Vendor


class UserRegisterForm(UserCreationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control",
                "required": "required",
            }
        )
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email Address",
                "class": "form-control",
                "required": "required",
            }
        )
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Password",
                "class": "form-control",
                "required": "required",
            }
        )
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm Password",
                "class": "form-control",
                "required": "required",
            }
        )
    )

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email is already existed.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username is already existed.")
        return username


class VendorRegisterForm(forms.ModelForm):
    title = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Shop Name", "class": "form-control", "required": "required"}))
    description = forms.CharField(widget=forms.Textarea(attrs={"placeholder": "Description", "class": "form-control", "rows": 3, "required": "required"}))
    address = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Address", "class": "form-control", "required": "required"}))
    contact = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "Contact Number", "class": "form-control", "required": "required"}))
    image = forms.ImageField(widget=forms.FileInput(attrs={"class": "form-control", "required": "required"}))
    cover_image = forms.ImageField(widget=forms.FileInput(attrs={"class": "form-control", "required": "required"}))

    class Meta:
        model = Vendor
        fields = ["title", "image", "cover_image", "description", "address", "contact"]


class ProfileForm(forms.ModelForm):
    full_name = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Full Name",
                "class": "form-control",
            }
        )
    )
    bio = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "placeholder": "Bio",
                "class": "form-control",
                "rows": 3,
            }
        ),
        required=False,
    )
    phone = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Phone Number",
                "class": "form-control",
            }
        ),
        required=False,
    )
    address = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Address",
                "class": "form-control",
            }
        ),
        required=False,
    )
    country = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Country",
                "class": "form-control",
            }
        ),
        required=False,
    )
    image = forms.ImageField(
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
            }
        ),
        required=False,
    )

    class Meta:
        model = Profile
        fields = ["image", "full_name", "bio", "phone", "address", "country"]


class UserUpdateForm(forms.ModelForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Username",
                "class": "form-control",
                "required": "required",
            }
        )
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email Address",
                "class": "form-control",
                "required": "required",
            }
        )
    )

    class Meta:
        model = User
        fields = ["username", "email"]
