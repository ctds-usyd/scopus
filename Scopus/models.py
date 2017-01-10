from django.db import models, transaction
from django.core.exceptions import MultipleObjectsReturned

# class Keywords(models.Model):
#     keyword = models.CharField(max_length=30)

class Source(models.Model):
    """A unique publication venue with respect to Scopus's source ID."""
    class Meta:
        db_table = 'source'
        unique_together = ('scopus_source_id', 'issn_print', 'issn_electronic')

    scopus_source_id = models.BigIntegerField(default=-1, null=False, blank=False,
                                       db_index=True, help_text="Scopus's srcid")
    source_type = models.CharField(max_length=1, db_index=True, null=True, help_text="Source type",
                                   choices = [('b', 'b = Book'),
                                              ('d', 'd = Trade Journal'),
                                              ('j', 'j = Journal'),
                                              ('k', 'k = Book Series'),
                                              ('m', 'm = Multi-volume Reference Works'),
                                              ('p', 'p = Conference Proceeding'),
                                              ('r', 'r = Report'),
                                              ('n', 'n = Newsletter'),
                                              ('w', 'w = Newspaper'),
                                              ])
    source_title = models.CharField(max_length=400, null=False, blank=False)
    source_abbrev = models.CharField(max_length=200, null=False, blank=False)
    issn_print = models.CharField(max_length=15, null=True, blank=False, db_index=True)
    issn_electronic = models.CharField(max_length=15, null=True, blank=False, db_index=True)

    @classmethod
    @transaction.atomic
    def get_or_create(cls, source_id, issn_print, issn_electronic):
        """
        To avoid creating multiple similar records by more than one thread.
        Note: get_or_create method in Django is not thread safe:
        http://stackoverflow.com/questions/6416213/is-get-or-create-thread-safe
        http://stackoverflow.com/questions/2235318/how-do-i-deal-with-this-race-condition-in-django
        """
        try:
            obj, created = cls.objects.get_or_create(source_id=source_id,
                                                     issn_print=issn_print,
                                                     issn_electronic=issn_electronic)
        except MultipleObjectsReturned:
            created = False
            obj = cls.objects.get(source_id=source_id,
                                  issn_print=issn_print,
                                  issn_electronic=issn_electronic)
        return obj, created

    def _type_label(self):
        return dict(self._meta.get_field('source_type').choices)[self.source_type]

    def __str__(self):
        return '<source[{}] {}: {}>'.format(self._type_label(), self.scopus_source_id, self.source_title)


class Document(models.Model):
    class Meta:
        db_table = 'document'

    eid = models.BigIntegerField(null=False, blank=False,
                                 db_index=True,
                                 primary_key=True,
                                 help_text='A unique identifier for the record; but see group_id')
    doi = models.CharField(max_length=150, null=True, help_text='DOI')
    pub_year = models.IntegerField(default=-1, null=False, blank=False,
                                   db_index=True,
                                   help_text='Publication year recorded in xocs:pub-year, backing off to xocs:sort-year where pub-year is unavailable')
    group_id = models.BigIntegerField(db_index=True, null=True, blank=True,
                                      help_text='An EID shared by likely duplicate doc entries')
    # keywords = models.ManyToManyField(Keywords)
    title = models.CharField(max_length=500, null=False, blank=False,
                             help_text='The original (untranslated) title')
    source = models.ForeignKey(Source, blank=True, null=True,
                               db_index=True, help_text='Where the document is published')
    citation_count = models.IntegerField(default=0, help_text='Citation count from citedby.xml')
    title_language = models.CharField(max_length=5, default='',
                                      help_text='The language of the original title')
    citation_type = models.CharField(max_length=5, default='',
                                     help_text='The type of document',
                                     choices=[
                                              ('ab', 'ab = Abstract Report'),
                                              ('ar', 'ar = Article'),
                                              ('ba', 'ba'),
                                              ('bk', 'bk = Book'),
                                              ('br', 'br = Book Review'),
                                              ('bz', 'bz = Business Article'),
                                              ('cb', 'cb = Conference Abstract'),
                                              ('ch', 'ch = Chapter'),
                                              ('cp', 'cp = Conference Paper'),
                                              ('cr', 'cr = Conference Review'),
                                              ('di', 'di = Dissertation'),
                                              ('ed', 'ed = Editorial'),
                                              ('er', 'er = Erratum'),
                                              ('ip', 'ip = Article in Press'),
                                              ('le', 'le = Letter'),
                                              ('no', 'no = Note'),
                                              ('pa', 'pa = Patent'),
                                              ('pr', 'pr = Press Release'),
                                              ('re', 're = Review'),
                                              ('rf', 'rf'),
                                              ('rp', 'rp = Report'),
                                              ('sh', 'sh = Short Survey'),
                                              ('wp', 'wp = Working Paper'),
                                     ])

    def _type_label(self):
        return dict(self._meta.get_field('citation_type').choices)[self.citation_type]

    def __str__(self):
        return '<doc[{}] {}>'.format(self._type_label(), self.eid)


class Authorship(models.Model):
    class Meta:
        db_table = 'authorship'

    document = models.ForeignKey(Document, null=False, db_index=True)
    author_id = models.BigIntegerField(null=True, blank=True, db_index=True, help_text="Scopus's auid")
    initials = models.CharField(max_length=20, default='')
    surname = models.CharField(max_length=100, null=False, blank=False)
    order = models.PositiveIntegerField(default=0, help_text='1 for first author, etc. Can have multiple Authorship entries for one value of order.')
    affiliation_id = models.IntegerField(db_index=True, null=True, help_text="Scopus's afid")
    organization = models.CharField(max_length=300, default='', db_index=True,
                                    help_text='Name from 1st organization node in affiliation details')
    department = models.CharField(max_length=200, default='',
                                  help_text='Name from 2nd organization node in affiliation details')
    country = models.CharField(max_length=10, null=False, blank=False)
    city = models.CharField(max_length=30, help_text='Not currently stored')

    def __str__(self):
        return '<{} {} ({}) is #{} author of <doc {}>>'.format(self.initials,
                                                         self.surname,
                                                         self.organization,
                                                         self.order,
                                                         self.document_id)


class ItemID(models.Model):
    class Meta:
        db_table = 'itemid'

    document = models.ForeignKey(Document, null=False, db_index=True)
    item_id = models.CharField(max_length=20, null=False, blank=False,
                               db_index=True, help_text='The identifier')
    item_type = models.CharField(max_length=40,
                                 help_text='ItemID type (see Scopus documentation)')

    def __str__(self):
        return '<itemid[{}] for {}>'.format(self.item_type, self.document)


class Citation(models.Model):
    class Meta:
        db_table = 'citation'

    cite_to = models.BigIntegerField(default=-1, null=False, db_index=True,
                                     help_text='EID of document being cited')
    cite_from = models.BigIntegerField(default=-1, null=False, db_index=True,
                                       help_text='EID (or group ID?) of citing document')

    def __str__(self):
        return '<{} cited {}>'.format(self.cite_from, self.cite_to)


class Abstract(models.Model):
    class Meta:
        db_table = 'abstract'

    document = models.ForeignKey(Document, null=False, db_index=True)
    abstract = models.TextField(max_length=10000, default='',
                                help_text='The article abstract')
    
    def __str__(self):
        return '<abstract for {}, {} chars>'.format(self.document, len(self.abstract))
