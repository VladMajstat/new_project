import re

from datetime import datetime, date

import phonenumbers

from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.views.decorators.http import require_POST, require_http_methods

from .models import (
    Candidate, HR, CandidateComment, HRComment, Department
)
from .forms import HRForm
from apps.core.breadcrumbs import breadcrumb, add_breadcrumb


User = get_user_model()


def format_phone_number(raw_phone):
    if not raw_phone: return None

    digits = re.sub(r'\D', '', str(raw_phone))

    if not digits: return None

    if len(digits) == 10 and digits.startswith('0'):
        digits = '38' + digits
    elif len(digits) == 11 and digits.startswith('80'):
        digits = '3' + digits

    if len(digits) == 12 and digits.startswith('380'):
        return f"{digits[:3]}-{digits[3:5]}-{digits[5:8]}-{digits[8:]}"
    return digits[:20]


@login_required
@breadcrumb("Home", "index")
def hr_profile(request, name):
    user = request.user

    if user.is_superuser:
        add_breadcrumb(request, f"HRs", 'hrs_list')
        hr = get_object_or_404(HR, name=name)
        add_breadcrumb(request, f"{hr.user.first_name} {hr.user.last_name}")
    elif not (hr := user.hr):
        return HttpResponse('Forbidden', status=403)
    else:
        add_breadcrumb(request, f"{user.first_name} {user.last_name}")


    if request.method == 'POST':
        text = request.POST.get('text')

        if text:
            HRComment.objects.create(
                hr=hr,
                user=request.user,
                text=text
            )
            return redirect('hr_profile', name=name)

    return render(request, 'hr_profile.html', {'hr': hr})


@login_required
@breadcrumb("Home", "index")
def hr_edit(request, name):
    target_hr = get_object_or_404(HR, name=name)
    target_user = target_hr.user

    is_owner = (request.user == target_user)
    is_admin = (request.user.is_superuser or request.user.is_staff)

    if not (is_owner or is_admin):
        return HttpResponse('Forbidden', status=403)

    profile_form = HRForm(instance=target_hr)
    password_form = None

    if is_owner:
        add_breadcrumb(
            request,
            f"{target_user.first_name} {target_user.last_name}", 'hr_profile',
            name=target_hr.name
        )
        add_breadcrumb(request, f"Edit")
        password_form = PasswordChangeForm(user=target_user)
    elif is_admin:
        add_breadcrumb(request, f"HRs", 'hrs_list')
        add_breadcrumb(request, f"Edit {target_user.first_name} {target_user.last_name}", name=target_hr.name)

    if request.method == 'POST':
        if 'submit_profile' in request.POST:
            profile_form = HRForm(request.POST, request.FILES, instance=target_hr)

            if profile_form.is_valid():
                profile_form.save()
                return redirect(request.path)

        elif 'submit_password' in request.POST and is_owner:
            password_form = PasswordChangeForm(user=target_user, data=request.POST)

            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                return redirect(request.path)
            else:
                messages.error(request, 'Password change failed. Please check errors.')

    context = {
        'profile_form': profile_form,
        'password_form': password_form,
        'hr': target_hr,
        'is_owner': is_owner
    }
    return render(request, 'hr_edit.html', context)


@login_required
@breadcrumb("Home", "index")
@breadcrumb("Candidates", "candidates_list")
def candidate_profile(request, pk):
    if not request.user.is_staff:
        return HttpResponse('Forbidden', status=403)

    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        text = request.POST.get('text')

        if text:
            CandidateComment.objects.create(
                candidate=candidate,
                user=request.user,
                text=text
            )
            return redirect('candidate_profile', pk=pk)

    add_breadcrumb(request, f"Candidates", 'candidates_list')
    add_breadcrumb(request, f"{candidate.first_name} {candidate.last_name}")

    return render(request, 'candidate_profile.html', {'candidate': candidate})


@login_required
@breadcrumb("Home", "index")
@breadcrumb("Candidates", "candidates_list")
def candidate_edit(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        raw_phone = request.POST.get('phone')
        source = request.POST.get('source')
        status = request.POST.get('status')
        city = request.POST.get('city')
        department_id = request.POST.get('department')
        telegram_link = request.POST.get('telegram_link')
        resume_link = request.POST.get('resume_link')

        birth_date = request.POST.get('birth_date')
        cover = request.POST.get('cover')
        photo = request.FILES.get('photo')

        age = calculate_age(birth_date)

        if not birth_date:
            birth_date = None

        department_obj = None
        if department_id:
            try:
                department_obj = Department.objects.get(pk=department_id)
            except Department.DoesNotExist:
                department_obj = None

        formatted_phone = candidate.phone
        if raw_phone:
            try:
                clean_raw = raw_phone.strip()

                try:
                    parsed_number = phonenumbers.parse("+" + clean_raw, None)
                except phonenumbers.NumberParseException:
                    parsed_number = phonenumbers.parse(clean_raw, "UA")

                if not phonenumbers.is_valid_number(parsed_number):
                    parsed_number = phonenumbers.parse(clean_raw, None)
                    if not phonenumbers.is_valid_number(parsed_number):
                        messages.error(request, "Entered phone number is invalid.")
                        return redirect('candidate_edit', pk=pk)

                country_code = str(parsed_number.country_code)
                nat_num = str(parsed_number.national_number)

                if len(nat_num) == 10:
                    formatted_phone = f"{country_code}-{nat_num[:3]}-{nat_num[3:6]}-{nat_num[6:]}"

                elif len(nat_num) == 9:
                    formatted_phone = f"{country_code}-{nat_num[:2]}-{nat_num[2:5]}-{nat_num[5:]}"

                else:
                    formatted_phone = f"{country_code}-{nat_num}"

            except phonenumbers.NumberParseException:
                messages.error(request, "Could not parse phone number.")
                return redirect('candidate_edit', pk=pk)

        if resume_link and Candidate.objects.filter(resume_link=resume_link).exclude(pk=pk).exists():
            messages.error(request, "Candidate with this resume link already exists.")
            return redirect('candidate_edit', pk=pk)

        if email and Candidate.objects.filter(email=email).exclude(pk=pk).exists():
            messages.error(request, f"Candidate with email '{email}' already exists.")
            return redirect('candidate_edit', pk=pk)

        if formatted_phone and Candidate.objects.filter(phone=formatted_phone).exclude(pk=pk).exists():
            messages.error(request, f"Candidate with phone '{formatted_phone}' already exists.")
            return redirect('candidate_edit', pk=pk)

        try:
            candidate.full_name = full_name
            candidate.email = email
            candidate.phone = formatted_phone
            candidate.source = source
            candidate.status = status
            candidate.city = city
            candidate.department = department_obj
            candidate.telegram_link = telegram_link
            candidate.resume_link = resume_link
            candidate.birth_date = birth_date
            candidate.age = age
            candidate.cover = cover

            if photo:
                candidate.profile_photo = photo

            candidate.save()

            messages.success(request, f"Candidate '{full_name}' successfully updated.")
            return redirect('candidate_edit', pk=pk)

        except Exception as e:
            messages.error(request, f"Database error: {e}")
            return redirect('candidate_edit', pk=pk)

    contexts = {
        'candidate': candidate,
        'departments': Department.objects.all(),
    }
    return render(request, 'candidate_edit.html', contexts)


@login_required
@breadcrumb("Home", "index")
@breadcrumb("Candidates", "candidates_list")
def candidates_list(request, slug=None):
    if slug:
        candidates = Candidate.objects.filter(department__slug=slug)
    else:
        candidates = Candidate.objects.all()

    name = request.GET.get('name', '').strip()
    email = request.GET.get('email', '').strip()
    phone = request.GET.get('phone', '').strip()
    selected_statuses = request.GET.getlist('statusFilter')

    if name:
        candidates = candidates.filter(full_name__icontains=name)
    if email:
        candidates = candidates.filter(email__icontains=email)
    if phone:
        clean_digits = ''.join(filter(str.isdigit, phone))
        if clean_digits:
            regex_pattern = ".*".join(clean_digits)
            candidates = candidates.filter(phone__iregex=regex_pattern)
        else:
            candidates = candidates.filter(phone__icontains=phone)
    if selected_statuses:
        candidates = candidates.filter(status__in=selected_statuses)

    sort_by = request.GET.get('sort', 'created')
    direction = request.GET.get('direction', 'desc')

    mapping = {
        'name': 'full_name',
        'email': 'email',
        'phone': 'phone',
        'created': 'created_at',
        'status': 'status',
        'updated': 'updated_at'
    }

    field = mapping.get(sort_by, 'created_at')

    if direction == 'asc':
        candidates = candidates.order_by(field)
    else:
        candidates = candidates.order_by(f'-{field}')

    paginator = Paginator(candidates, 100)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    departments = Department.objects.all()

    context = {
        'page_obj': page_obj,
        'departments': departments,
        'selected_statuses': selected_statuses,
        'candidates_count': candidates.count(),
        'department': slug,
        'current_sort': sort_by,
        'current_direction': direction,
    }

    return render(request, 'candidates.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def candidate_comments_api(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == "POST":
        text = request.POST.get('text')
        if text:
            comment = CandidateComment.objects.create(
                user=request.user,
                candidate=candidate,
                text=text
            )
            return JsonResponse({
                'status': 'success',
                'comment': {
                    'user': comment.user.first_name or comment.user.username,
                    'text': comment.text,
                    'date': comment.created_at.strftime('%Y-%m-%d %H:%M')
                }
            })
        return JsonResponse({'status': 'error'}, status=400)

    comments = candidate.comments.select_related('user').order_by('-created_at')
    data = []
    for c in comments:
        data.append({
            'user': c.user.first_name or c.user.username,
            'text': c.text,
            'date': c.created_at.strftime('%Y-%m-%d %H:%M')
        })

    return JsonResponse({'comments': data})


@login_required
def candidate_delete(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)

    if request.method == 'POST':
        candidate.delete()
        return redirect('candidates_list')

    return redirect('candidates_list')


def calculate_age(birth_date_str):
    if not birth_date_str:
        return None
    try:
        born = datetime.strptime(birth_date_str, "%Y-%m-%d").date()
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (ValueError, TypeError):
        return None


@login_required
@breadcrumb("Home", "index")
@breadcrumb("Candidates", "candidates_list")
@breadcrumb("Add Candidate", None)
def candidate_add(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        raw_phone = request.POST.get('phone')
        source = request.POST.get('source')
        status = request.POST.get('status')
        city = request.POST.get('city')
        department_id = request.POST.get('department')
        telegram_link = request.POST.get('telegram_link')
        resume_link = request.POST.get('resume_link')

        birth_date = request.POST.get('birth_date')
        cover = request.POST.get('cover')
        photo = request.FILES.get('photo')

        age = calculate_age(birth_date)

        if not birth_date:
            birth_date = None

        if not full_name:
            fname = request.POST.get('first_name', '')
            lname = request.POST.get('last_name', '')
            full_name = f"{fname} {lname}".strip()

        department_obj = None
        if department_id:
            try:
                department_obj = Department.objects.get(pk=department_id)
            except Department.DoesNotExist:
                department_obj = None

        formatted_phone = None
        if raw_phone:
            try:
                parsed_number = phonenumbers.parse(raw_phone, "UA")

                if not phonenumbers.is_valid_number(parsed_number):
                    messages.error(request, "Entered phone number is invalid.")
                    return redirect('candidate_add')

                country_code = str(parsed_number.country_code)
                nat_num = str(parsed_number.national_number)

                if len(nat_num) == 9:
                    formatted_phone = f"{country_code}-{nat_num[:2]}-{nat_num[2:5]}-{nat_num[5:]}"
                elif len(nat_num) == 10:
                    formatted_phone = f"{country_code}-{nat_num[:3]}-{nat_num[3:6]}-{nat_num[6:]}"
                else:
                    formatted_phone = f"{country_code}-{nat_num}"
            except phonenumbers.NumberParseException:
                messages.error(request, "Could not parse phone number.")
                return redirect('candidate_add')

        if resume_link and Candidate.objects.filter(resume_link=resume_link).exists():
            messages.error(request, "Candidate with this resume link already exists.")
            return redirect('candidate_add')

        if email and Candidate.objects.filter(email=email).exists():
            messages.error(request, f"Candidate with email '{email}' already exists.")
            return redirect('candidate_add')

        if formatted_phone and Candidate.objects.filter(phone=formatted_phone).exists():
            messages.error(request, f"Candidate with phone '{formatted_phone}' already exists.")
            return redirect('candidate_add')

        try:
            Candidate.objects.create(
                full_name=full_name,
                email=email,
                phone=formatted_phone,
                source=source,
                status=status,
                city=city,
                department=department_obj,
                telegram_link=telegram_link,
                resume_link=resume_link,
                profile_photo=photo,
                birth_date=birth_date,
                age=age,
                cover=cover
            )
            messages.success(request, f"Candidate '{full_name}' successfully added.")
            return redirect('candidates_list')

        except Exception as e:
            messages.error(request, f"Database error: {e}")
            return redirect('candidate_add')

    contexts = {
        'departments': Department.objects.all(),
        'selected_department': request.GET.get('department')
    }
    return render(request, 'main_app/candidate_add.html', contexts)


@require_POST
def update_candidate_status(request, pk):
    candidate = get_object_or_404(Candidate, pk=pk)
    new_status = request.POST.get('status')

    if new_status in Candidate.Status.values:
        candidate.status = new_status
        candidate.save()
        return JsonResponse({'status': 'success', 'new_status': new_status})
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid status'}, status=400)
