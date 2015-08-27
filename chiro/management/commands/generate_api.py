import importlib, inspect, re
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from tastypie.resources import Resource
from tastypie import fields

class Command(BaseCommand):
    help = 'Generate BackBone models API'

    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='+')
        parser.add_argument('--api', '-a', default='v1', help='API version name')

    def handle(self, *args, **options):
        self.api_name = options.get('api', '')
        self.models = []
        for app_name in options['apps']:
            app = apps.get_app_config(app_name)
            resources = importlib.import_module(app.name + '.api.resources')
            for name, res in resources.__dict__.items():
                if name in ['ModelResource', 'Resource']:
                    continue
                name = self.make_name(name)
                if inspect.isclass(res) and issubclass(res, Resource):
                    self.generate(name, res)

    def generate(self, name, res):
        api_name = 'api.model.%s'%name.lower()

        # Seems to be a race-condition with this... ?
        ii = 0
        while 1:
            url = res().get_resource_uri()
            if url or ii == 100:
                break
            ii += 1

        self.stdout.write('\'%s\': \'%s\','%(api_name, url))

    def make_name(self, name):
        ridx = name.rfind('Resource')
        return name[:ridx]
