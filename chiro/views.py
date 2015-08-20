from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie

class APIViewMixin(object):

    def get_context_data(self, **kwargs):
        ctx = super(APIViewMixin, self).get_context_data(**kwargs)
        ctx['data'] = self.get_server_data()
        return ctx

    def get_server_data(self, **kwargs):
        return kwargs

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(APIViewMixin, self).dispatch(*args, **kwargs)
