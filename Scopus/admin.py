from django.contrib import admin

from . import models

# Hide default auth display in admin

from django.contrib.auth.models import User
from django.contrib.auth.models import Group

admin.site.unregister(User)
admin.site.unregister(Group)

# TODO: display Citations on Document
# TODO: display non-ForeignKey IDs as if they were


def _field_names(model):
    return [field.name for field in model._meta.get_fields() if not field.related_model]


class AbstractInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = False
    model = models.Abstract


class AuthorshipInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True
    model = models.Authorship


class ItemIDInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True
    model = models.ItemID


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    readonly_fields = _field_names(models.Document)
    inlines = [
        AbstractInline,
        AuthorshipInline,
        ItemIDInline,
    ]
    search_fields = ('eid', 'title', 'authorship__surname')


@admin.register(models.Source)
class SourceAdmin(admin.ModelAdmin):
    readonly_fields = _field_names(models.Source)
    search_fields = ('source_id', 'source_title', 'source_abbrev', 'issn_print', 'issn_electronic')


@admin.register(models.Authorship)
class AuthorshipAdmin(admin.ModelAdmin):
    search_fields = ('surname', 'organization', 'author_id', 'affiliation_id')
    readonly_fields = _field_names(models.Authorship)
    fields = (('author_id', 'document', 'order'),
              ('initials', 'surname'),
              ('affiliation_id', 'organization', 'department'),
              ('country', 'city'))


@admin.register(models.Citation)
class CitationAdmin(admin.ModelAdmin):
    readonly_fields = _field_names(models.Citation)
