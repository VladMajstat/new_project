from django.db import models

from ckeditor.fields import RichTextField


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(null=True, max_length=100, unique=True)

    def __str__(self):
        return self.name


class Blog(models.Model):
    title = models.CharField(null=True, max_length=100)
    description = RichTextField(null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now=True)

    tags = models.ManyToManyField(Tag, blank=True, related_name='blogs')

    meta_title = models.CharField(null=True, max_length=100)
    meta_description = models.TextField(null=True)

    def __str__(self):
        return self.title
