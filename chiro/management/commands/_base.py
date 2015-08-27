import inflect, re, os, difflib

class CommandMixin(object):

    def add_arguments(self, parser):
        super(CommandMixin, self).add_arguments(parser)
        parser.add_argument('--destination', '-d', default='.', help='output path')
        parser.add_argument('--namespace', '-n', help='add a namespace to files')

    def handle(self, *args, **options):
        self.destination = options.get('destination', '.')
        self.namespace = options.get('namespace', '')

    def output(self, content, filename):
        path = os.path.join(self.destination, filename)
        if os.path.exists(path):
            with open(path, 'r') as file:
                orig = file.read()
            if orig != content:
                diff = difflib.Differ().compare(orig.splitlines(), content.splitlines())
                self.stdout.write('\n')
                self.stdout.write('\n'.join(diff))
                resp = self.query_yes_no('"%s" exists and has been manually changed, overwrite?'%path, default='no')
                if not resp:
                    path += '.new'
            else:
                return
        with open(path, 'w') as file:
            file.write(content)

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
