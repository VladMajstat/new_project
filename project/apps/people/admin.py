from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import HR, Candidate, HRComment, CandidateComment, Department, Job


User = get_user_model()


class BaseProfileForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), required=False, label='Password')

    first_name = forms.CharField(label='First name', required=False)
    last_name = forms.CharField(label='Last name', required=False)
    email = forms.EmailField(label='Email', required=False)
    phone = forms.CharField(label='Phone', required=False, max_length=32)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # При редактировании подтягиваем данные из User
        if self.instance.pk and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            self.fields['password'].help_text = "Leave empty, if you want save current password"
        else:
            self.fields['password'].required = True

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name

        query = User.objects.filter(username=name)
        if self.instance.pk and self.instance.user:
            query = query.exclude(pk=self.instance.user.pk)

        if query.exists():
            raise forms.ValidationError(f"User with such login already exists.")

        return name

    def save(self, commit=True):
        profile = super().save(commit=False)

        # Используем name как username
        target_username = self.cleaned_data.get('name')

        password = self.cleaned_data['password']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        email = self.cleaned_data['email']

        # --- СОЗДАНИЕ (Create) ---
        if not profile.pk:
            user = User.objects.create_user(
                username=target_username,  # <--- Вот здесь подставляем name
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email,
            )
            profile.user = user

        else:
            if profile.user:
                user = profile.user
                user.username = target_username
                user.first_name = first_name
                user.last_name = last_name
                user.email = email

                if password:
                    user.set_password(password)

                if commit:
                    user.save()

        if commit:
            profile.save()

        return profile


# --- Формы моделей ---

class HRAdminForm(BaseProfileForm):
    class Meta:
        model = HR
        exclude = ['user']


@admin.register(HR)
class HRAdmin(admin.ModelAdmin):
    form = HRAdminForm

    fields = (
        'name',
        'password',
        'first_name',
        'last_name',
        'phone',
        'email',
        'profile_photo',
    )

    list_display = ('id', 'name', 'get_full_name', 'phone')

    @admin.display(description='Full name')
    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}" if obj.user else "-"


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    pass


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    pass


@admin.register(CandidateComment)
class CandidateCommentAdmin(admin.ModelAdmin):
    pass


@admin.register(HRComment)
class HRCommentAdmin(admin.ModelAdmin):
    pass


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    pass
