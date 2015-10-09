import importlib, inspect, re, os
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from tastypie.resources import Resource
from tastypie import fields
from ._base import CommandMixin

model_tmpl = '''///
/// @file      {file_name}.js
/// @namespace {namespace}
///
/// {model_name} definition.
///

var $ = require( 'jquery' );
var _ = require( 'underscore' );
var Backbone = require( 'backbone' );
var Relational = require( 'backbone-relational' );
var Validation = require( 'backbone.validation' );
{dependencies}

///
/// {model_name} definition.
///
var {model_name} = Backbone.RelationalModel.extend({{
    urlRoot: {url},
    defaults: function() {{
        return {{
            {defaults}
        }};
    }},
    relations: [{relations}],
    validation: {{
    }}
}});

module.exports = {model_name};
'''

collection_tmpl = '''///
/// @file      {collection_file_name}.js
/// @namespace {namespace}
///
/// {collection_name} collection definition.
///

var $ = require( 'jquery' );
var _ = require( 'underscore' );
var Backbone = require( 'backbone' );
var {model_name} = require( '../models/{file_name}' );

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

module.exports = {collection_name};
'''

wrapper_tmpl = '''///
/// @file      model.js
/// @namespace {namespace}
///
/// All models convenience wrapper.
///

var Backbone = require( 'backbone' );
var Relational = require( 'backbone-relational' );
{models}

// Cache the models in an object initially so we can then use
// that object as a scope for backbone relational.
var scope = {{
{map}
}};

// Have to update the Backbone store to find the models.
Backbone.Relational.store.addModelScope( scope );

// Now pass it back.
modules.exports = scope;
'''

class Command(CommandMixin, BaseCommand):
    help = 'Generate BackBone models from Tastypie API'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('apps', nargs='+')
        parser.add_argument('--api', '-a', default='v1', help='API version name')

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
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
            'models': '\n'.join(['var %s = require( \'./%s/%s\' );'%(m[1], m[2], m[0]) for m in self.models]),
            'map': ',\n'.join(['    %s: %s'%(m[1], m[1]) for m in self.models]),
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
                defaults.append('%s: new %s()'%(field_name, self.get_related_model(field)))
            elif isinstance(field, fields.ToManyField):
                related.append(self.generate_related(field_name, field, 'HasMany'))
            else:
                defaults.append('%s: \'\''%field_name)

        # Seems to be a race-condition with this... ?
        ii = 0
        while 1:
            # url = res().get_resource_uri()
            url = 'sd.get( \'api.model.%s\' )'%name.lower()
            if url or ii == 100:
                break
            ii += 1

        values = {
            'file_name': re.sub(r'([a-z])([A-Z])', r'\g<1>_\g<2>', name).lower(),
            'namespace': self.namespace,
            'model_name': name,
            'file_dependencies': ['\'%s\''%re.sub(r'([a-z])([A-Z])', r'\g<1>_\g<2>', d).lower() for d in self.dependencies],
            'model_dependencies': [os.path.basename(d) for d in self.dependencies],
            'url': '%s'%url,
            'defaults': ',\n            '.join(defaults),
            'relations': ', '.join(related),
            # 'validation': ',\n                '.join(['%s: {}'%d for d in defaults]),
            'collection_file_name': re.sub(r'([a-z])([A-Z])', r'\g<1>_\g<2>', self.collection).lower(),
            'collection_name': self.collection,
        }
        # if values['file_dependencies']:
        #     values['file_dependencies'] += ', '
        # if values['model_dependencies']:
        #     values['model_dependencies'] = ', ' + values['model_dependencies']
        values['dependencies'] = ''
        for file_dep, model_dep in zip(values['file_dependencies'], values['model_dependencies']):
            values['dependencies'] += 'var %s = require( %s );\n'%(model_dep, file_dep)
        self.output(model_tmpl.format(**values), values['file_name'] + '.js', sub='models')
        self.output(collection_tmpl.format(**values), values['collection_file_name'] + '.js', sub='collections')
        self.models.extend([
            (values['file_name'], values['model_name'], 'models'),
            (values['collection_file_name'], values['collection_name'], 'collections'),
        ])

    def generate_related(self, name, field, type):
        related_model = self.get_related_model(field)
        if related_model not in self.dependencies:
            self.dependencies.append('./%s'%related_model)
        if type == 'HasMany':
            related_collection = self.pluralize(related_model)
            if related_collection not in self.dependencies:
                self.dependencies.append('../collections/%s'%related_collection)
            related_collection = '\n        collectionType: %s,'%related_collection
        else:
            related_collection = ''
        if self.namespace:
            reverse_collection_type = ',\n            collectionType: \'%s\''%self.collection
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
