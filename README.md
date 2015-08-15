# django-chiro
A place for some tools to help massage Django + BackBone into shape.

## Generating Models

This tool generates a set of BackBone (+ BackBone relational) models from a TastyPie API. Run it
via the Django managment commands:

```bash
./manage.py generate_models app_to_convert -n myNamespace -d ./app/static/js/destination
```

TODO: Get around to explaining this more...
