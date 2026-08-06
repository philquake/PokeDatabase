from django.urls import path
from . import views

urlpatterns = [
    path(
        "pokemon/<str:name>/",
        views.PokemonDetailView.as_view(),
        name="pokemon-detail"
    ),
]
