# frontend/views.py

from django.views.generic import TemplateView

class FrontendAppView(TemplateView):
    # Po prostu pokaż ten plik HTML
    template_name = "frontend/index.html"