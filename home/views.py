from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
def home(request):
    return render(request, 'home.html')

def search(request):
    return render(request, 'search.html')
    