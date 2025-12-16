from html.parser import HTMLParser
import sys

class DivChecker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.unexpected_closings = []
        self.opens = 0
        self.closes = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'div':
            self.opens += 1
            self.stack.append(self.getpos())

    def handle_endtag(self, tag):
        if tag.lower() == 'div':
            self.closes += 1
            if self.stack:
                self.stack.pop()
            else:
                # unexpected closing
                self.unexpected_closings.append(self.getpos())

if __name__ == '__main__':
    path = 'index.html'
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = f.read()
    except Exception as e:
        print('ERROR: cannot read', path, e)
        sys.exit(2)

    parser = DivChecker()
    parser.feed(data)

    print('Total <div> openings:', parser.opens)
    print('Total </div> closings:', parser.closes)
    if parser.unexpected_closings:
        print('\nUnexpected closing </div> at positions (line, col):')
        for pos in parser.unexpected_closings:
            print('-', pos)
    if parser.stack:
        print('\nUnclosed <div> openings (missing </div>) at positions (line, col):')
        for pos in parser.stack:
            print('-', pos)

    if not parser.unexpected_closings and not parser.stack:
        print('\nAll <div> tags appear balanced (count and nesting for <div> matched).')
    else:
        print('\nFound mismatches. Please inspect the reported positions.')
