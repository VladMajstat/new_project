import sys
import os
from io import BytesIO

from PIL import Image, ImageOps

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import models
from django.db.models.functions import Concat
from django.contrib.auth import get_user_model
from django.utils import timezone

from pytils.translit import slugify


User = get_user_model()


def process_image(image_file, target_size, name_suffix):
    if not image_file:
        return None

    img = Image.open(image_file)
    img = ImageOps.exif_transpose(img)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    img = ImageOps.fit(img, target_size, Image.LANCZOS)

    output_io = BytesIO()
    img.save(output_io, format='JPEG', quality=85, optimize=True)
    output_io.seek(0)

    filename = os.path.splitext(image_file.name)[0]
    new_filename = f"{filename}_{name_suffix}.jpg"

    return InMemoryUploadedFile(
        output_io,
        'ImageField',
        new_filename,
        'image/jpeg',
        sys.getsizeof(output_io),
        None
    )


class HRManager(models.Manager):
    def get_queryset(self):
        # При каждом запросе мы "склеиваем" имя и фамилию через пробел
        return super().get_queryset().annotate(
            full_name=Concat('user__first_name', models.Value(' '), 'user__last_name')
        )


class HR(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='hr')
    name = models.CharField(null=True, blank=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

    profile_photo = models.ImageField(null=True, upload_to='hr/photos', blank=True)
    avatar = models.ImageField(
        null=True,
        upload_to='hr/avatars',
        blank=True,
        editable=False
    )

    objects = HRManager()

    def __str__(self):
        if hasattr(self, 'full_name'):
            return self.full_name
        return f"{self.user.first_name} {self.user.last_name}"

    def save(self, *args, **kwargs):
        is_new_photo = True
        if self.pk:
            try:
                old_obj = HR.objects.get(pk=self.pk)
                if old_obj.profile_photo == self.profile_photo:
                    is_new_photo = False
            except HR.DoesNotExist:
                pass

        if self.profile_photo and is_new_photo:
            self.avatar = process_image(self.profile_photo, (100, 100), 'avatar')

            self.profile_photo = process_image(self.profile_photo, (300, 400), 'profile')

        super().save(*args, **kwargs)

    @property
    def pretty_phone(self):
        if not self.phone:
            return "—"

        p = str(self.phone)

        if p.startswith('+38'):
            p = p[3:]
        elif p.startswith('38'):
            p = p[2:]

        if p.startswith('-'):
            p = p[1:]

        if p.startswith('0-'):
            p = '0' + p[2:]

        return p


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Генерируем slug только если он пустой
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)


class Job(models.Model):
    url = models.URLField(unique=True)
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Candidate(models.Model):
    class Source(models.TextChoices):
        RESPONSE = 'Response', 'Response'
        CONTACTS = 'Contacts', 'Contacts',
        APPLIED = 'Applied', 'Applied'

    class Status(models.TextChoices):
        NEW = 'New', 'New'
        TELEGRAM = 'Telegram', 'Telegram'
        NO_ANSWER = 'No Answer', 'No Answer'
        TEST = 'Test', 'Test'
        TRAINEE = 'Trainee', 'Trainee'
        WORKING = 'Working', 'Working'
        REFUSE = 'Refuse', 'Refuse'

    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    full_name = models.CharField(max_length=200, null=True, blank=True) # временное поле
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        blank=True,
        null=True
    )
    status = models.CharField(
        max_length=20,
        blank=True,
        choices=Status.choices,
        default=Status.NEW,
        null=True
    )
    email = models.EmailField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True)
    profile_photo = models.ImageField(null=True, upload_to='candidates/photos', blank=True)
    avatar = models.ImageField(
        null=True,
        upload_to='candidates/avatars',
        blank=True,
        editable=False
    )
    photo_link = models.URLField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    telegram_link = models.URLField(null=True, blank=True)
    resume_link = models.URLField(null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    cover = models.TextField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.full_name}"

    @property
    def pretty_phone(self):
        if not self.phone:
            return "—"

        p = str(self.phone)

        if p.startswith('+38'):
            p = p[3:]
        elif p.startswith('38'):
            p = p[2:]

        if p.startswith('-'):
            p = p[1:]

        if p.startswith('0-'):
            p = '0' + p[2:]

        return p

    def save(self, *args, **kwargs):
        is_new_photo = True

        if self.pk:
            try:
                old_instance = Candidate.objects.get(pk=self.pk)

                if old_instance.status != self.status:
                    self.updated_at = timezone.now()

                if old_instance.profile_photo == self.profile_photo:
                    is_new_photo = False

            except Candidate.DoesNotExist:
                pass

        # Логика полного имени
        if not self.full_name:
            f_name = self.first_name or ""
            l_name = self.last_name or ""
            self.full_name = f"{f_name} {l_name}".strip()

        if self.profile_photo and is_new_photo:
            self.avatar = process_image(self.profile_photo, (100, 100), 'avatar')
            self.profile_photo = process_image(self.profile_photo, (300, 400), 'profile')

        super().save(*args, **kwargs)


class BaseComment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True  # Эта модель не создаст таблицу в БД, она шаблон
        ordering = ['-created_at']


class CandidateComment(BaseComment):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='comments')

    def __str__(self):
        return f"Comment on {self.candidate}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new:
            self.candidate.updated_at = timezone.now()
            self.candidate.save(update_fields=['updated_at'])


class HRComment(BaseComment):
    hr = models.ForeignKey(HR, on_delete=models.CASCADE, related_name='comments')

    def __str__(self):
        return f"Comment on {self.hr}"
