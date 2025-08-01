from django.contrib import admin
from userauths.models import User, Profile, ContactUs


class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "username", "date_joined"]  # Sửa bio thành date_joined
    list_filter = ["date_joined", "is_active", "is_staff"]
    search_fields = ["email", "username"]


class ContactUsAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "subject", "date"]
    list_filter = ["date"]
    search_fields = ["full_name", "email", "subject"]
    readonly_fields = ["date"]


class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "bio", "phone", "verified"]
    list_filter = ["verified"]
    search_fields = ["user__username", "user__email", "full_name"]


admin.site.register(User, UserAdmin)
admin.site.register(ContactUs, ContactUsAdmin)
admin.site.register(
    Profile, ProfileAdmin
)  # Sử dụng ProfileAdmin thay vì register trống
