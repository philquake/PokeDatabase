from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

# Create your views here.
def home(request):
    return render(request, 'home.html')

def search(request):
    return render(request, 'search.html')


def pokedex(request):
    return HttpResponse("Pokédex")


def types(request):
    return HttpResponse("Types")


def region(request):
    return HttpResponse("Region")


def abilities(request):
    return HttpResponse("Abilities")


def moves(request):
    return HttpResponse("Moves")


def competitive(request):
    return HttpResponse("Competitive")
    