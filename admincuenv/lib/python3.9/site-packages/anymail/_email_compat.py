# Work around bugs in older versions of email.parser.Parser
#
# This module implements two classes:
#   EmailParser
#   EmailBytesParser
# which can be used like the Python 3.3+ email.parser.Parser
# and email.parser.BytesParser (with email.policy.default).
#
# On Python 2.7, they attempt to work around some bugs/limitations
# in email.parser.Parser, without trying to back-port the whole
# Python 3 email package.

__all__ = ['EmailParser', 'EmailBytesParser']


from email.parser import Parser

try:
    # With Python 3.3+ (email6) package, using `policy=email.policy.default`
    # avoids earlier bugs. (Note that Parser defaults to policy=compat32,
    # which *preserves* earlier bugs.)
    from email.policy import default
    from email.parser import BytesParser

    class EmailParser(Parser):
        def __init__(self, _class=None, policy=default):  # don't default to compat32 policy
            super(EmailParser, self).__init__(_class, policy=policy)

    class EmailBytesParser(BytesParser):
        def __init__(self, _class=None, policy=default):  # don't default to compat32 policy
            super(EmailBytesParser, self).__init__(_class, policy=policy)

except ImportError:
    # Pre-Python 3.3 email package: try to work around some bugs
    from email.header import decode_header
    from collections import deque

    class EmailParser(Parser):
        def parse(self, fp, headersonly=False):
            # Older Parser doesn't correctly unfold headers (RFC5322 section 2.2.3).
            # Help it out by pre-unfolding the headers for it.
            fp = HeaderUnfoldingWrapper(fp)
            message = Parser.parse(self, fp, headersonly=headersonly)

            # Older Parser doesn't decode RFC2047 headers, so fix them up here.
            # (Since messsage is fully parsed, can decode headers in all MIME subparts.)
            for part in message.walk():
                part._headers = [  # doesn't seem to be a public API to easily replace all headers
                    (name, _decode_rfc2047(value))
                    for name, value in part._headers]
            return message

    class EmailBytesParser(EmailParser):
        def parsebytes(self, text, headersonly=False):
            # In Python 2, bytes is str, and Parser.parsestr uses bytes-friendly cStringIO.StringIO.
            return self.parsestr(text, headersonly)

    class HeaderUnfoldingWrapper:
        """
        A wrapper for file-like objects passed to email.parser.Parser.parse which works
        around older Parser bugs with folded email headers by pre-unfolding them.

        This only works for headers at the message root, not ones within a MIME subpart.
        (Accurately recognizing subpart headers would require parsing mixed-content boundaries.)
        """

        def __init__(self, fp):
            self.fp = fp
            self._in_headers = True
            self._pushback = deque()

        def _readline(self, limit=-1):
            try:
                line = self._pushback.popleft()
            except IndexError:
                line = self.fp.readline(limit)
                # cStringIO.readline doesn't recognize universal newlines; splitlines does
                lines = line.splitlines(True)
                if len(lines) > 1:
                    line = lines[0]
                    self._pushback.extend(lines[1:])
            return line

        def _peekline(self, limit=-1):
            try:
                line = self._pushback[0]
            except IndexError:
                line = self._readline(limit)
                self._pushback.appendleft(line)
            return line

        def readline(self, limit=-1):
            line = self._readline(limit)
            if self._in_headers:
                line_without_end = line.rstrip("\r\n")  # CRLF, CR, or LF -- "universal newlines"
                if len(line_without_end) == 0:
                    # RFC5322 section 2.1: "The body ... is separated from the header section
                    # by an empty line (i.e., a line with nothing preceding the CRLF)."
                    self._in_headers = False
                else:
                    # Is this header line folded? Need to check next line...
                    # RFC5322 section 2.2.3: "Unfolding is accomplished by simply removing any CRLF
                    # that is immediately followed by WSP." (WSP is space or tab)
                    next_line = self._peekline(limit)
                    if next_line.startswith((' ', '\t')):
                        line = line_without_end
            return line

        def read(self, size):
            if self._in_headers:
                # For simplicity, just read a line at a time while in the header section.
                # (This works because we know email.parser.Parser doesn't really care if it reads
                # more or less data than it asked for -- it just pushes it into FeedParser either way.)
                return self.readline(size)
            elif len(self._pushback):
                buf = ''.join(self._pushback)
                self._pushback.clear()
                return buf
            else:
                return self.fp.read(size)

    def _decode_rfc2047(value):
        result = value
        decoded_segments = decode_header(value)
        if any(charset is not None for raw, charset in decoded_segments):
            # At least one segment is an RFC2047 encoded-word.
            # Reassemble the segments into a single decoded string.
            unicode_segments = []
            prev_charset = None
            for raw, charset in decoded_segments:
                if (charset is None or prev_charset is None) and unicode_segments:
                    # Transitioning to, from, or between *non*-encoded segments:
                    # add back inter-segment whitespace that decode_header consumed
                    unicode_segments.append(u" ")
                decoded = raw.decode(charset, 'replace') if charset is not None else raw
                unicode_segments.append(decoded)
                prev_charset = charset
            result = u"".join(unicode_segments)
        return result
