from django.shortcuts import render
from .models import Category

def category_view(request):
    categories = Category.objects.prefetch_related('subcategories').all()
    search_query = request.GET.get('search', '')

    if search_query:
        categories = categories.filter(subcategories__name__icontains=search_query).distinct()

    return render(request, 'homepage.html', {'categories': categories, 'search_query': search_query})
