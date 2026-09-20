"""Reference boundaries independent of the edition's paragraph structure."""
from html import escape


def milestone(urn=None, *, unit='prayer-part'):
    """Open a correspondence, or close the current unit without naming a new one."""
    ref = f' corresp="{escape(urn, quote=True)}"' if urn else ''
    return f'<tei:milestone unit="{escape(unit, quote=True)}"{ref}/>'


def marked(urn, text, *, unit='prayer-part'):
    """A bounded passage, including any markup in its already-encoded text."""
    return milestone(urn, unit=unit) + text + milestone(unit=unit)


class Correspondences:
    """Consecutive units share boundaries; interruptions explicitly close the scope.

    Call close before an unaddressed quotation or a speaker rubric, and at the end
    of the sequence. A paragraph break alone need not interrupt the sequence.
    """
    def __init__(self):
        self.unit = None

    def start(self, urn, *, unit=None):
        unit = unit or ('verse' if ':bible:' in urn else 'prayer-part')
        boundary = self.close() if self.unit != unit else ''
        self.unit = unit
        return boundary + milestone(urn, unit=unit)

    def close(self):
        boundary = milestone(unit=self.unit) if self.unit else ''
        self.unit = None
        return boundary
