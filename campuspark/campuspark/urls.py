"""
URL configuration for campuspark project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from campuspark_aluno import views as aluno_views
from campuspark_operador import views as operador_views

urlpatterns = [
    #rota, view responsavel, nome da rota

    path('', operador_views.inicio, name='inicio'),

    # campuspark_aluno
    # path('', aluno_views.aluno_home, name='inicio'),
    # path('aluno/', aluno_views.aluno_home, name='inicio'),


    # campuspark_operador
    path('operador/', operador_views.inicio, name='inicio'),
]
