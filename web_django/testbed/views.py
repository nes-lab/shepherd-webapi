from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import ObserverForm
from .models import Observer

# TODO: total guesswork


@login_required(login_url='/accounts/login/')
@require_http_methods(['POST', 'GET'])
def observer_add(request):
    if request.method == 'POST':
        form = ObserverForm(request.POST)
    else:
        form = ObserverForm()
    return render(request, 'add_element.html', {'form': form})
