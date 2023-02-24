from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render

# from django.utils import timezone
from django.views.decorators.http import require_http_methods

# from django.views.generic import DetailView
from django.views.generic import ListView

from .forms import ObserverForm
from .models import Observer

# TODO: mostly guesswork


def index(request):
    return HttpResponse("You're looking at the basic Testbed Overview")


@login_required(login_url="/accounts/login/")
@require_http_methods(["POST", "GET"])
def observer_add(request):
    if request.method == "POST":
        form = ObserverForm(request.POST)
        if form.is_valid():
            form.save()
            # return redirect('testbed') # TODO
    else:
        form = ObserverForm()
    return render(request, "add_element.html", {"form": form})


def observer_view(request, observer_name):
    return HttpResponse("You're looking at the Observer-Change for %s" % observer_name)


@login_required(login_url="/accounts/login/")
def observer_change(request, observer_name):
    return HttpResponse("You're looking at the Observer-Change for %s" % observer_name)


# @login_required(login_url='/accounts/login/')
class ObserversView(ListView):
    # TODO: only playground
    model = Observer
    template_name = "templates/testbed/observers_table.html"


#    def get_context_data(self, **kwargs):
#        context = super().get_context_data(**kwargs)
#        context["now"] = timezone.now()
#        return context

# TODO: try https://github.com/jieter/django-tables2/
