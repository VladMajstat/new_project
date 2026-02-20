from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Blog, Category
from apps.core.breadcrumbs import breadcrumb, add_breadcrumb


@breadcrumb("Home", "index")
@breadcrumb("Blogs", "blogs_list")
def blog_list(request, category=None):

    if category:
        blogs = Blog.objects.filter(category__name=category)
    else:
        blogs = Blog.objects.all()

    paginator = Paginator(blogs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()

    return render(request, 'blogs.html', {'page_obj': page_obj, 'categories': categories})

@breadcrumb("Home", "index")
@breadcrumb("Blogs", "blogs_list")
def blog_detail(request, pk):

    blog = Blog.objects.get(pk=pk)

    add_breadcrumb(
        request, f"{blog.title}"
    )
    return render(request, 'blog.html', {'blog': blog})
