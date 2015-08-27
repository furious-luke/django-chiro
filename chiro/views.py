from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from .serial import Resource as Resource

class APIViewMixin(object):

    def get_context_data(self, **kwargs):
        ctx = super(APIViewMixin, self).get_context_data(**kwargs)
        ctx['data'] = self.get_server_data()
        return ctx

    def get_server_data(self, **kwargs):
        return kwargs

    def resource(self, resource, **kwargs):
        obj = resource.obj_get(resource.build_bundle(request=self.request), **kwargs)
        bundle = resource.build_bundle(obj=obj, request=self.request)
        return Resource(resource, bundle)

    @method_decorator(ensure_csrf_cookie)
    def dispatch(self, *args, **kwargs):
        return super(APIViewMixin, self).dispatch(*args, **kwargs)
