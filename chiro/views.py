from django.shortcuts import render
from django.http import JsonResponse
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

class AjaxFormViewMixin(object):

    def form_valid(self, form):
        if self.request.is_ajax():
            return JsonResponse({
                'status': 200,
                'content': {
                    'status': 'success',
                    'redirect': self.get_success_url(),
                }
            })
        else:
            super(AjaxFormViewMixin, self).form_valid(form)

    def form_invalid(self, form):
        if self.request.is_ajax():
            return JsonResponse({
                'status': 200,
                'content': {
                    'status': 'error',
                    'errors': form.errors,
                }
            })
        else:
            super(AjaxFormViewMixin, self).form_invalid(form)
