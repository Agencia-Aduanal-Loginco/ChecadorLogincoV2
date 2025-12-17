from django.shortcuts import render
from django.views.generic import TemplateView


class FacialRecognitionView(TemplateView):
    """Vista para la interfaz de reconocimiento facial"""
    template_name = 'facial_recognition.html'


def facial_recognition_page(request):
    """Vista simple para renderizar la página de reconocimiento facial"""
    return render(request, 'facial_recognition.html')
