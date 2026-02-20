from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.conf import settings

import phonenumbers

from apps.core.breadcrumbs import breadcrumb


User = get_user_model()


if settings.FEATURES['PEOPLE']:
    from apps.people.models import HR


    @login_required
    @breadcrumb("Home", "index")
    @breadcrumb("HRs", "hrs_list")
    def hrs_list(request):
        hr_name = request.GET.get('hr_name')
        if hr_name:
            hrs = HR.objects.filter(name=hr_name)
        else:
            hrs = HR.objects.all()

        name = request.GET.get('name', '').strip()
        email = request.GET.get('email', '').strip()
        phone = request.GET.get('phone', '').strip()

        if name:
            hrs = hrs.filter(full_name__icontains=name)
        if email:
            hrs = hrs.filter(user__email__icontains=email)
        if phone:
            clean_digits = ''.join(filter(str.isdigit, phone))
            if clean_digits:
                regex_pattern = ".*".join(clean_digits)
                hrs = hrs.filter(phone__iregex=regex_pattern)
            else:
                hrs = hrs.filter(phone__icontains=phone)

        sort_by = request.GET.get('sort', 'name')
        direction = request.GET.get('direction', 'asc')

        mapping = {
            'name': 'user__first_name',
            'email': 'user__email',
            'phone': 'phone',
        }

        ordering_field = mapping.get(sort_by, 'user__first_name')

        if direction == 'asc':
            hrs = hrs.order_by(ordering_field)
        else:
            hrs = hrs.order_by(f'-{ordering_field}')
        # ---------------------

        paginator = Paginator(hrs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'hrs.html', {
            'page_obj': page_obj,
            'current_sort': sort_by,
            'current_direction': direction,
        })

    @login_required
    def hr_delete(request, pk):
        hr = get_object_or_404(HR, pk=pk)

        if request.method == 'POST':
            hr.delete()
            messages.success(request, 'HR deleted successfully.')
            return redirect('hrs_list')

        return redirect('hrs_list')


    @login_required
    @breadcrumb("Home", "index")
    @breadcrumb("HRs", "hrs_list")
    @breadcrumb("Add HR", None)
    def hr_add(request):
        if request.method == 'POST':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')

            raw_phone = request.POST.get('phone')

            photo = request.FILES.get('photo')
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            username = request.POST.get('username')

            if password != password2:
                messages.error(request, "Passwords do not match.")
                return redirect('hr_add')

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect('hr_add')

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return redirect('hr_add')

            formatted_phone = None
            if raw_phone:
                try:
                    parsed_number = phonenumbers.parse(raw_phone, "UA")

                    if not phonenumbers.is_valid_number(parsed_number):
                        messages.error(request, "Invalid phone number.")
                        return redirect('hr_add')

                    country_code = str(parsed_number.country_code)
                    nat_num = str(parsed_number.national_number)

                    if len(nat_num) == 9:  #
                        formatted_phone = f"{country_code}-{nat_num[:2]}-{nat_num[2:5]}-{nat_num[5:]}"

                    elif len(nat_num) == 10:
                        formatted_phone = f"{country_code}-{nat_num[:3]}-{nat_num[3:6]}-{nat_num[6:]}"

                    else:
                        formatted_phone = f"{country_code}-{nat_num}"

                except phonenumbers.NumberParseException:
                    messages.error(request, "Invalid phone number format.")
                    return redirect('hr_add')

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True
            )

            HR.objects.create(
                user=user,
                profile_photo=photo,
                phone=formatted_phone,
                name=username
            )

            return redirect('hrs_list')

        return render(request, 'main_app/hr_add.html')
else:
    @login_required
    def admin_panel(request):

        if request.method == 'POST':
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            username = request.POST.get('username')

            if password != password2:
                messages.error(request, "Passwords do not match.")
                return redirect('admin_panel')

            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
                return redirect('admin_panel')

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return redirect('admin_panel')

            User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=True
            )

            messages.success(request, f"User created successfully.")
            return redirect('admin_panel')

        return render(request, 'main_app/admin_panel.html')



