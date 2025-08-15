from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from userauths.forms import UserRegisterForm, ProfileForm, VendorRegisterForm
from userauths.models import User, Profile
from core.models import Vendor


@login_required
def vendor_register_view(request):
    if request.user.is_superuser:
        messages.warning(request, "You are already a vendor.")
        return redirect("useradmin:dashboard")

    if request.method == "POST":
        form = VendorRegisterForm(request.POST, request.FILES)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.user = request.user
            vendor.save()

            user = request.user
            user.is_staff = True
            user.is_superuser = True
            user.save()

            messages.success(request, "Vendor account created successfully! You can now access the vendor dashboard.")
            return redirect("useradmin:dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = VendorRegisterForm()

    context = {
        "form": form,
    }
    return render(request, "userauths/vendor_register.html", context)


def register_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("core:index")

    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            messages.success(
                request,
                f"Account {username} has been successfully created! Please log in.",
            )

            # Redirect to the login page instead of auto-login
            return redirect("userauths:sign-in")
        else:
            messages.error(request, "Please check your registration information again.")
    else:
        form = UserRegisterForm()

    context = {
        "form": form,
    }
    return render(request, "userauths/sign-up.html", context)


def login_view(request):
    if request.user.is_authenticated:
        messages.warning(request, f"Hey you are already Logged In.")
        return redirect("core:index")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            # Check if user exists
            user = User.objects.get(email=email)

            # If user exists, try to authenticate
            user = authenticate(request, email=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "You are logged in.")
                return redirect("core:index")
            else:
                # User exists but password is incorrect
                messages.warning(request, "Incorrect password.")

        except User.DoesNotExist:
            # User doesn't exist
            messages.warning(request, f"User with {email} does not exist")

    return render(request, "userauths/sign-in.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You logged out.")
    return redirect("userauths:sign-in")


@login_required
def profile_update(request):
    # Tạo profile nếu chưa có
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            new_form = form.save(commit=False)
            new_form.user = request.user
            new_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("core:dashboard")
    else:
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
        "profile": profile,
    }

    return render(request, "userauths/profile-edit.html", context)
