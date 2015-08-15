import importlib, inspect, inflect, re, os
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from tastypie.resources import Resource
from tastypie import fields

model_tmpl = '''///
/// @file      {file_name}.js
/// @namespace {namespace}
///
/// {model_name} definition.
///

define(
    [ {file_dependencies} ],
    function( {model_dependencies} ) {{

        ///
        /// {model_name} definition.
        ///
        var {model_name} = Backbone.RelationalModel.extend({{
            urlRoot: {url},
            defaults: {{
                {defaults}
            }},
            relations: [{relations}],
            validation: {{
                {validation}
            }}
        }});

        return {model_name};
    }}
);
'''

collection_tmpl = '''///
/// @file      {collection_file_name}.js
/// @namespace {namespace}
///
/// {collection_name} collection definition.
///

define(
    [ '{file_name}' ],
    function( {model_name} ) {{

        ///
        /// {collection_name} collection definition.
        ///
        var {collection_name} = Backbone.Collection.extend({{
            model: {model_name},
            url: {url},
            parse: function( response ) {{
                return response.objects;
            }}
        }});

        return {collection_name};
    }}
);
'''

wrapper_tmpl = '''///
/// @file      models.js
/// @namespace {namespace}
///
/// All models convenience wrapper.
///

define(
    [ {files} ],
    function( {models} ) {{
        return {{
{map}
        }};
    }}
);
'''

class Command(BaseCommand):
    help = 'Generate BackBone models from Tastypie API'

    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='+')
        parser.add_argument('--destination', '-d', default='.', help='output path')
        parser.add_argument('--namespace', '-n', help='add a namespace to files')
        parser.add_argument('--api', '-a', default='v1', help='API version name')

    def handle(self, *args, **options):
        self.destination = options.get('destination', '.')
        self.namespace = options.get('namespace', '')
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
        self.generate_wrapper()

    def generate_wrapper(self):
        self.models.sort(key=lambda x: x[0])
        values = {
            'namespace': self.namespace,
            'files': ', '.join(['\'%s\''%m[0] for m in self.models]),
            'models': ', '.join(['%s'%m[1] for m in self.models]),
            'map': ',\n'.join(['            %s: %s'%(m[1], m[1]) for m in self.models]),
        }
        self.output(wrapper_tmpl.format(**values), 'models.js')

    def generate(self, name, res):
        self.collection = self.pluralize(name)
        self.dependencies = list()
        defaults = []
        related = []
        all_fields = [(k, v) for k, v in res.base_fields.items()]
        all_fields.sort(key=lambda x: x[0])
        for field_name, field in all_fields:
            if field_name in ['resource_uri', 'id']:
                continue
            if isinstance(field, fields.ForeignKey):
                related.append(self.generate_related(field_name, field, 'HasOne'))
            elif isinstance(field, fields.ToManyField):
                related.append(self.generate_related(field_name, field, 'HasMany'))
            else:
                defaults.append(field_name)

        # Seems to be a race-condition with this... ?
        ii = 0
        while 1:
            url = res().get_resource_uri()
            if url or ii == 100:
                break
            ii += 1

        values = {
            'file_name': re.sub(r'([a-z])([A-Z])', r'\g<1>_\g<2>', name).lower(),
            'namespace': self.namespace,
            'model_name': name,
            'file_dependencies': ', '.join(['\'%s\''%re.sub(r'([a-z])([A-Z])', r'\g<1>_\g<2>', d).lower() for d in self.dependencies]),
            'model_dependencies': ', '.join(self.dependencies),
            'url': '\'%s\''%url,
            'defaults': ',\n                '.join(['%s: \'\''%d for d in defaults]),
            'relations': ', '.join(related),
            'validation': ',\n                '.join(['%s: {}'%d for d in defaults]),
            'collection_file_name': re.sub(r'([a-z])([A-Z])', r'\g<1>_\g<2>', self.collection).lower(),
            'collection_name': self.collection,
        }
        self.output(model_tmpl.format(**values), values['file_name'] + '.js')
        self.output(collection_tmpl.format(**values), values['collection_file_name'] + '.js')
        self.models.extend([
            (values['file_name'], values['model_name']),
            (values['collection_file_name'], values['collection_name']),
        ])

    def output(self, content, filename):
        path = os.path.join(self.destination, filename)
        if os.path.exists(path):
            with open(path, 'r') as file:
                orig = file.read()
            if orig != content:
                resp = self.query_yes_no('"%s" exists and has been manually changed, overwrite?'%path, default='no')
                if not resp:
                    path += '.new'
            else:
                return
        with open(path, 'w') as file:
            file.write(content)

    def generate_related(self, name, field, type):
        related_model = self.get_related_model(field)
        if related_model not in self.dependencies:
            self.dependencies.append(related_model)
        if type == 'HasMany':
            related_collection = self.pluralize(related_model)
            if related_collection not in self.dependencies:
                self.dependencies.append(related_collection)
            related_collection = '\n                collectionType: %s,'%related_collection
        else:
            related_collection = ''
        if self.namespace:
            reverse_collection_type = ',\n                    collectionType: \'%s.%s\''%(self.namespace, self.collection)
        else:
            reverse_collection_type = ''
        values = {
            'type': 'Backbone.%s'%type,
            'key': name,
            'related_model': related_model,
            'collection': related_collection,
            'plural': self.collection.lower(),
            'reverse_collection_type': reverse_collection_type,
        }
        return '''{{
                type: {type},
                key: '{key}',
                relatedModel: {related_model},{collection}
                includeInJSON: 'tastypie',
                reverseRelation: {{
                    key: '{plural}',
                    includeInJSON: false{reverse_collection_type}
                }}
            }}'''.format(**values)

    def get_related_model(self, field):
        txt = str(field.to_class)
        lidx = txt.rfind('.')
        ridx = txt.rfind('Resource')
        return txt[lidx + 1:ridx]

    def make_name(self, name):
        ridx = name.rfind('Resource')
        return name[:ridx]

    def pluralize(self, name):
        if name:
            words = re.sub(r'([a-z])([A-Z])', '\g<1> \g<2>', name).split()
            words[-1] = inflect.engine().plural(words[-1].lower())
            plural = list(''.join(words))
            for ii in range(len(name)):
                if name[ii].isupper():
                    plural[ii] = plural[ii].upper()
            return ''.join(plural)
        else:
            return ''

    def query_yes_no(self, question, default="yes"):
        """Ask a yes/no question via raw_input() and return their answer.

        "question" is a string that is presented to the user.
        "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

        The "answer" return value is True for "yes" or False for "no".
        """
        valid = {"yes": True, "y": True, "ye": True,
                 "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            self.stdout.write(question + prompt)
            choice = input().lower()
            if default is not None and choice == '':
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                self.stdout.write("Please respond with 'yes' or 'no' "
                                  "(or 'y' or 'n').\n")
