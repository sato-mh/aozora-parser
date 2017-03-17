from collections import defaultdict
import json
import os
import re
import subprocess
from aozora_bunko import AozoraBunko, Section, Paragraph, Sentence, Chunk, Morph
import util


class AozoraComponent(object):

    def __init__(self, meta_data, header, footer, sections):
        self.meta_data = meta_data
        self.header = header
        self.footer = footer
        self.headlines = list(sections.keys())
        self.sections = sections  # {headline: [line1, line2, ...]}

    def get_section(self, headline):
        if headline not in self.headlines:
            return None
        return '\n'.join(self.sections[headline])


class AozoraParser(object):
    '''
    Input: Aozora Bunko document formatted by text
           or intermidiate directry path
    '''

    def __init__(self):
        self.aozora_parser = AozoraParserForTextFormat()
        self.cabocha_parser = CabochaParser()

    def _create_aozora_bunko(self, meta_data, header, footer, section_d):
        sections = []
        for headline, cabocha_iter in section_d.items():
            paragraphs = self.cabocha_parser.parse(cabocha_iter)
            sections.append(Section(paragraphs, headline))
        return AozoraBunko(meta_data, header, footer, sections)

    def parse(self, aozora_text):
        aozora_component = self.aozora_parser.parse(aozora_text)
        section_d = {}
        for headline in aozora_component.headlines:
            text = aozora_component.get_section(headline)
            res = subprocess.run(['cabocha', '-f1'],
                                 input=text,
                                 stdout=subprocess.PIPE,
                                 encoding='utf-8')
            section_d[headline] = res.stdout.split('\n')
        return self._create_aozora_bunko(
            meta_data=aozora_component.meta_data,
            header=aozora_component.header,
            footer=aozora_component.footer,
            section_d=section_d
        )

    def save_intermidiate(self, aozora_text, dst_path='data/intermidiate'):
        aozora_component = self.aozora_parser.parse(aozora_text)
        # create directry
        if not os.path.exists(dst_path):
            os.makedirs(dst_path)
        sct_path = os.path.join(dst_path, 'sections')
        if not os.path.exists(sct_path):
            os.mkdir(sct_path)

        # save intermidiate
        for k, v in aozora_component.__dict__.items():
            if k == 'sections':
                continue
            if k == 'meta_data':
                with open(os.path.join(dst_path, f'{k}.json'), 'w') as f:
                    json.dump(v, f, ensure_ascii=False)
                continue
            with open(os.path.join(dst_path, f'{k}.txt'), 'w') as f:
                f.write('\n'.join(v))
        for i, headline in enumerate(aozora_component.headlines):
            text = aozora_component.get_section(headline)
            with open(os.path.join(sct_path, f'{i:02d}.txt'), 'w') as f:
                subprocess.run(['cabocha', '-f1'],
                               input=text,
                               stdout=f,
                               encoding='utf-8')

    def parse_from_intermidiate(self, src_path='data/intermidiate'):
        file_names = ['meta_data.json', 'header.txt', 'footer.txt',
                      'headlines.txt']
        for fn in file_names:
            with open(os.path.join(src_path, fn)) as f:
                if fn == 'meta_data.txt':
                    meta_data = json.load(f)
                if fn == 'header.txt':
                    header = list(f)
                if fn == 'footer.txt':
                    footer = list(f)
                if fn == 'headlines.txt':
                    headline_d = {f'{i:02d}.txt': l.rstrip()
                                  for i, l in enumerate(f)}

        sct_path = os.path.join(src_path, 'sections')
        section_d = {}
        for s in sorted(os.listdir(sct_path)):
            with open(os.path.join(sct_path, s)) as f:
                section_d[headline_d[s]] = list(f)
        return self._create_aozora_bunko(meta_data, header, footer, section_d)


class CabochaParser(object):
    '''
    * Input: text parsed by Cabocha with latice format

    < latice format >
    表層形\t品詞,品詞細分類1,品詞細分類2,品詞細分類3,活用型,活用形,原形,読み,発音
    '''

    def __init__(self):
        pass

    def parse(self, data):
        paragraphs = []
        sentences = []
        chunks = []
        morphs = []
        srcs = defaultdict(list)
        src = 0
        is_prev_line_EOS = False
        for line in data:
            line = line.rstrip()
            if line == '':
                continue
            if line.startswith('* '):
                splitted = line.strip().split(' ')
                dst = int(splitted[2][:-1])
                src = int(splitted[1])
                srcs[dst].append(src)
                if len(morphs) == 0:
                    continue
                chunks.append(Chunk(morphs, dst, srcs[src]))
                morphs = []
                continue
            if line == 'EOS':
                chunks.append(Chunk(morphs, dst, srcs[src]))
                morphs = []
                sentences.append(Sentence(chunks))
                chunks = []
                if is_prev_line_EOS:
                    paragraphs.append(Paragraph(sentences))
                    sentences = []
                    continue
                is_prev_line_EOS = True
                continue
            surface, attrs = line.split('\t')
            attrs = attrs.split(',')
            # deal with unknown words
            for _ in range(9 - len(attrs)):
                attrs.append('*')

            args = {
                'surface': surface,
                'pos': attrs[0],
                'pos1': attrs[1],
                'pos2': attrs[2],
                'pos3': attrs[3],
                'ctype': attrs[4],
                'cform': attrs[5],
                'base': attrs[6],
                'literal': attrs[7],
                'pronunciation': attrs[8]
            }
            morphs.append(Morph(**args))
            is_prev_line_EOS = False
        paragraphs.append(Paragraph(sentences))
        return paragraphs


class AozoraParserForTextFormat(object):
    '''
    Input: Aozora Bunko document formatted by text
    '''

    def __init__(self):
        self.data = None
        self.header_pattern = re.compile('^-+$')
        self.footer_pattern = re.compile('(底本：)|(［＃本文終わり］)')
        self.headline_pattern = re.compile('［＃「(.+)」は(.{1})見出し］')
        self.ruby_pattern = re.compile('｜|(《.+?》)')
        self.accent_pattern = re.compile('〔.+?〕')
        self.annotation_pattern = re.compile('［＃.+?］')

    def _is_header_start(self, line, is_header):
        return not is_header and self.header_pattern.match(line)

    def _is_header_end(self, line, is_header):
        return is_header and self.header_pattern.match(line)

    def _is_footer_start(self, line):
        return self.footer_pattern.match(line)

    def _get_meta_data(self, data):
        meta_lines = []
        for line in data:
            line = line.strip()
            if line == '':
                break
            meta_lines.append(line)
        meta_size = len(meta_lines)
        meta_data = {
            'title': '',
            'subtitle': '',
            'author': '',
            'translator': '',
        }

        # may be another pattern
        meta_lines = list(reversed(meta_lines))
        if meta_size == 0:
            return meta_data
        meta_data['title'] = meta_lines.pop()
        if meta_size == 2:
            meta_data['author'] = meta_lines.pop()
            return meta_data
        meta_data['subtitle'] = meta_lines.pop()
        meta_data['author'] = meta_lines.pop()
        if meta_size == 3:
            return meta_data
        if meta_size == 4:
            meta_data['translator'] = meta_lines.pop()

        return meta_data

    def _split_into_header_footer_body(self, data):
        is_header = False
        header = []
        is_footer = False
        footer = []
        body = []
        for line in data:
            line = line.rstrip()
            # header
            if self._is_header_end(line, is_header):
                is_header = False
                header.append(line)
                continue
            if self._is_header_start(line, is_header):
                is_header = True
            if is_header:
                header.append(line)
                continue
            # footer
            if self._is_footer_start(line):
                is_footer = True
            if is_footer:
                footer.append(line)
                continue
            # body
            body.append(line)
        return header, footer, body

    def _split_into_sentences(self, line):
        sentences = []
        # TODO: consider another way
        for l in line.replace('。', '。\n').split('\n'):
            if l == '':
                continue
            sentences.append(l.strip())
        return sentences

    def _parse_section(self, lines):
        sentences = []
        for line in lines:
            line = self.ruby_pattern.sub('', line)
            line = self.accent_pattern.sub('', line)
            line = self.annotation_pattern.sub('', line)
            if line == '':
                continue
            sentences.extend(self._split_into_sentences(line))
            sentences.append('')  # add line breaks for each paragraph
        return sentences

    def _parse_body(self, body):
        sections = {}
        lines_in_section = []
        next_headline = ''
        for line in body:
            if line == '':
                continue
            match = self.headline_pattern.search(line)
            if match is None:
                lines_in_section.append(line)
                continue
            if len(lines_in_section) > 0:
                sections[next_headline] = self._parse_section(lines_in_section)
                lines_in_section = []
            next_headline = match.group(1)
        sections[next_headline] = self._parse_section(lines_in_section)
        return sections

    def parse(self, data):
        if data is None:
            return None
        meta_data = self._get_meta_data(data)

        header, footer, body = self._split_into_header_footer_body(data)
        sections = self._parse_body(body)

        return AozoraComponent(meta_data, header, footer, sections)


def main():
    file_obj = util.get_file_obj()
    aozora_parser = AozoraParser()
    # waganeko = aozora_parser.parse(file_obj)
    aozora_parser.save_intermidiate(file_obj)
    # waganeko = aozora_parser.parse_from_intermidiate()
    # print(waganeko.get_headlines())
    # print(waganeko.get_meta_data())
    # print(waganeko.get_header_text())
    # print(waganeko.get_footer_text())
    # print(waganeko.body[0].headline)
    # print(waganeko.body[0].get_text())


if __name__ == '__main__':
    main()
