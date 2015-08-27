from json import JSONEncoder, loads

class Resource(object):

    def __init__(self, resource, bundle):
        self.resource = resource
        self.bundle = bundle

    def __str__(self):
        res = self.resource
        bdl = self.bundle
        return res.serialize(None, res.full_dehydrate(bdl), 'application/json')

class ResourceEncoderMixin(object):

    def default(self, obj):
        try:
            if isinstance(obj, Resource):
                return loads(str(obj))
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return super(ResourceEncoderMixin, self).default(obj)

class ResourceEncoder(ResourceEncoderMixin, JSONEncoder):
    pass
