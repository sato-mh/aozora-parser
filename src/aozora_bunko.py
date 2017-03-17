class AozoraBunko(object):

    def __init__(self, meta_data, header, footer, body):
        self.title = meta_data.get('title', '')
        self.subtitle = meta_data.get('subtitle', '')
        self.author = meta_data.get('author', '')
        self.translator = meta_data.get('translator', '')
        self.header = header
        self.footer = footer
        self.body = body
        self._validate()

    def _validate(self):

        def execute(target, elem_type):
            if type(target) == list:
                types = [type(line) for line in target if type(line) != elem_type]
                if len(types) > 0:
                    raise
            else:
                raise

        def execute_header():
            try:
                execute(self.header, str)
            except:
                raise TypeError('header is Invalid.')

        def execute_footer():
            try:
                execute(self.footer, str)
            except:
                raise TypeError('footer is Invalid.')

        def execute_body():
            try:
                execute(self.body, Section)
            except:
                raise TypeError('body is Invalid.')

        execute_header()
        execute_footer()
        execute_body()

    def get_headlines(self):
        headlines = [s.headline for s in self.body]
        return '\n'.join(headlines)

    def get_meta_data(self):
        meta_data = [self.title, self.subtitle, self.author, self.translator]
        return '\n'.join([d for d in meta_data if d != ''])

    def get_header_text(self):
        return '\n'.join(self.header)

    def get_footer_text(self):
        return '\n'.join(self.footer)

    def get_text(self, title=False, author=False, header=False,
                 footer=False, headline=False, style='normal'):
        text = []
        if title:
            text.append(self.title)
        if author:
            text.append([self.author, ''])
        if header:
            text.extend(['\n'.join(self.header), ''])
        for section in self.body:
            text.extend([section.get_text(headline, style=style)])
        if footer:
            text.extend(['', '', '', '\n'.join(self.footer)])
        return '\n'.join(text)


class Section(object):

    def __init__(self, paragraphs, headline):
        self.headline = headline
        self.paragraphs = paragraphs

    def get_text(self, headline=False, style='normal'):
        text = []
        if headline:
            text.extend(['', self.headline, ''])
        text.append('\n'.join([p.get_text(style=style) for p in self.paragraphs]))
        return '\n'.join(text)


class Paragraph(object):

    def __init__(self, sentences):
        self.sentences = sentences

    def get_text(self, style='normal'):
        return '\n'.join([s.get_text(style=style) for s in self.sentences])


class Sentence(object):

    def __init__(self, chunks):
        self.chunks = chunks

    def get_text(self, style='normal'):
        if style == 'normal':
            return self._get_normal_text()
        if style == 'wakati':
            return self._get_wakachi_text()

    def _get_normal_text(self):
        return ''.join([''.join(c.get_surfaces()) for c in self.chunks])

    def _get_wakachi_text(self):
        return ' '.join([' '.join(c.get_surfaces()) for c in self.chunks])


class Chunk(object):

    def __init__(self, morphs, dst, srcs):
        self.morphs = morphs
        self.dst = dst
        self.srcs = srcs

    def get_surfaces(self):
        return [m.surface for m in self.morphs]

    def get_bases(self):
        return [m.base for m in self.morphs]


class Morph(object):

    def __init__(self, **kwargs):
        self.surface = kwargs.get('surface')
        self.base = kwargs.get('base')
        self.pos = kwargs.get('pos')
        self.pos1 = kwargs.get('pos1')
        self.pos2 = kwargs.get('pos2')
        self.pos3 = kwargs.get('pos3')
        self.ctype = kwargs.get('ctype')
        self.cform = kwargs.get('cform')
        self.base = kwargs.get('base')
        self.literal = kwargs.get('literal')
        self.pronunciation = kwargs.get('pronunciation')
