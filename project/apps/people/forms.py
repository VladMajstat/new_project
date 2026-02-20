from django import forms
from django.core.exceptions import ValidationError

from .models import HR, Candidate
from django.contrib.auth import get_user_model

import phonenumbers


User = get_user_model()


class HRForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = HR
        fields = ['profile_photo', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            user_data = self.instance.user
            self.fields['first_name'].initial = user_data.first_name
            self.fields['last_name'].initial = user_data.last_name
            self.fields['email'].initial = user_data.email

    def clean_phone(self):
        raw_phone = self.cleaned_data.get('phone')
        if not raw_phone:
            return raw_phone

        parsed_number = None

        # Спроба 1: Парсимо як є (з пріоритетом UA)
        try:
            parsed_number = phonenumbers.parse(raw_phone, "UA")
        except phonenumbers.NumberParseException:
            pass  # Якщо помилка парсингу, йдемо до спроби 2

        # Якщо перша спроба не дала валідного номеру, спробуємо додати "+"
        if parsed_number is None or not phonenumbers.is_valid_number(parsed_number):
            try:
                # Додаємо плюс, якщо його немає, і пробуємо ще раз
                if not raw_phone.startswith('+'):
                    parsed_number = phonenumbers.parse(f"+{raw_phone}", None)
            except phonenumbers.NumberParseException:
                pass

        # Фінальна перевірка: чи є у нас валідний номер після всіх спроб?
        if parsed_number is None or not phonenumbers.is_valid_number(parsed_number):
            raise forms.ValidationError("Invalid phone number or format.")

        # --- Форматування ---
        country_code = str(parsed_number.country_code)
        nat_num = str(parsed_number.national_number)

        # Формат для України (380-XX-XXX-XXXX)
        if len(nat_num) == 9:
            return f"{country_code}-{nat_num[:2]}-{nat_num[2:5]}-{nat_num[5:]}"

        # Формат для США та інших (1-XXX-XXX-XXXX)
        elif len(nat_num) == 10:
            return f"{country_code}-{nat_num[:3]}-{nat_num[3:6]}-{nat_num[6:]}"

        # Універсальний формат для інших
        else:
            return f"{country_code}-{nat_num}"

    def save(self, commit=True):
        hr_instance = super().save(commit=commit)

        if hr_instance.user:
            user_instance = hr_instance.user
            user_instance.first_name = self.cleaned_data.get('first_name')
            user_instance.last_name = self.cleaned_data.get('last_name')
            user_instance.email = self.cleaned_data.get('email')

            if commit:
                user_instance.save()

        return hr_instance


class CandidateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['email'].required = False
        self.fields['phone'].required = False
        self.fields['resume_link'].required = False

        if 'telegram_link' in self.fields:
            self.fields['telegram_link'].required = False

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'

    class Meta:
        model = Candidate
        exclude = ['created_at', 'avatar', 'first_name', 'last_name']

    def clean_email(self):
        email = self.cleaned_data.get('email')

        if not email:
            return email

        email = email.strip()

        duplicates = Candidate.objects.filter(email=email)

        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise ValidationError(f"Candidate with email '{email}' already exists.")

        return email

    def clean_resume_link(self):
        resume_link = self.cleaned_data.get('resume_link')

        if not resume_link:
            return resume_link

        resume_link = resume_link.strip()

        duplicates = Candidate.objects.filter(resume_link=resume_link)

        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)

        if duplicates.exists():
            raise ValidationError("Candidate with this resume link already exists.")

        return resume_link

    def clean_phone(self):
        raw_phone = self.cleaned_data.get('phone')

        if not raw_phone:
            return raw_phone

        raw_phone = raw_phone.strip()
        formatted_phone = None

        try:
            parsed_number = phonenumbers.parse(raw_phone, "UA")

            if not phonenumbers.is_valid_number(parsed_number):
                try:
                    parsed_with_plus = phonenumbers.parse("+" + raw_phone, "UA")
                    if phonenumbers.is_valid_number(parsed_with_plus):
                        parsed_number = parsed_with_plus
                    else:
                        raise ValidationError("Invalid phone number format.")
                except phonenumbers.NumberParseException:
                    raise ValidationError("Invalid phone number format.")

            country_code = str(parsed_number.country_code)
            nat_num = str(parsed_number.national_number)

            if len(nat_num) == 9:
                formatted_phone = f"{country_code}-{nat_num[:2]}-{nat_num[2:5]}-{nat_num[5:]}"
            elif len(nat_num) == 10:
                formatted_phone = f"{country_code}-{nat_num[:3]}-{nat_num[3:6]}-{nat_num[6:]}"
            else:
                formatted_phone = f"{country_code}-{nat_num}"

        except phonenumbers.NumberParseException:
            raise ValidationError("Could not parse phone number.")

        # 3. Проверка на дубликаты уже отформатированного номера
        if formatted_phone:
            duplicates = Candidate.objects.filter(phone=formatted_phone)

            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)

            if duplicates.exists():
                raise ValidationError(f"Candidate with phone '{formatted_phone}' already exists.")

        return formatted_phone