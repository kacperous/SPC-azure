from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    """
    Main frontend page - Hello World with API integration
    """
    context = {
        'title': 'Hello World',
        'message': 'Witaj w Django!',
        'description': 'Frontend w Django komunikuje się z API (user app)'
    }
    return render(request, 'frontend/index.html', context)
