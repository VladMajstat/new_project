from django.contrib import admin
from .models import Blog, Category, Tag


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    pass

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(Tag)
class CategoryAdmin(admin.ModelAdmin):
    pass