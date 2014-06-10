""" Resource definition."""
from . import six
import inspect
import logging
from django.db import models

from .utils import Choices
from .serializers import Serializer

__all__ = 'Resource',

logger = logging.getLogger(__name__)


class ResourceManager(object):

    """ Resource utils functionality."""

    @staticmethod
    def get_resource_name(meta):
        """ Define resource name based on Meta information.

        :param Resource.Meta meta: resource metainformation
        :return: name of resource
        :rtype: str

        """
        name = getattr(meta, 'name', None)
        if name is not None:
            return name
        else:
            return ResourceManager.get_concrete_model(meta)._meta.model_name

    @staticmethod
    def get_concrete_model(meta):
        """ Get model defined in Meta.

        :param Resource.Meta meta: resource metainformation
        :return: model or None
        :rtype django.db.models.Model or None:
        :raise ValueError: model is not found

        """
        model = getattr(meta, 'model', None)

        if model is None:
            return None

        if isinstance(model, six.string_types) and len(model.split('.')) == 2:
            app_name, model_name = model.split('.')
            return models.get_model(app_name, model_name)
        elif inspect.isclass(model) and issubclass(model, models.Model):
            return model
        else:
            raise ValueError("{0} is not a Django model".format(model))

    @staticmethod
    def get_model_fields(model):
        """ Get fields for model.

        :return dict: fields

        """
        if model is None:
            return None

        options = model._meta
        fields = {}

        for field in options.fields:
            if field.rel is None:
                if field.serialize or field.name == 'id':
                    fields[field.name] = {
                        "type": Resource.FIELD_TYPES.OWN,
                        "name": field.name,
                    }
            else:
                if field.rel.multiple:
                    # ForeignKey
                    print(field.rel.to)
                    logger.debug(
                        Resource.FIELD_TYPES.TO_ONE,
                        field.name,
                        field.rel,
                        field.serialize
                    )
                else:
                    # Multiple Table Inheritance
                    pass

        for field in options.many_to_many:
            pass
            #print(field.name, field.rel, field.serialize)

        # Check storage for relationship with this model.
        return fields


class ResourceMeta(type):

    """ Metaclass for JSON:API resources."""

    def __new__(mcs, name, bases, attrs):
        cls = super(ResourceMeta, mcs).__new__(mcs, name, bases, attrs)
        cls.Meta.name = ResourceManager.get_resource_name(cls.Meta)
        cls.Meta.name_plural = "{0}s".format(cls.Meta.name)
        cls.Meta.model = ResourceManager.get_concrete_model(cls.Meta)
        cls.Meta.fields = ResourceManager.get_model_fields(cls.Meta.model)
        return cls


@six.add_metaclass(ResourceMeta)
class Resource(object):

    """ Base JSON:API resource class."""

    FIELD_TYPES = Choices(
        ('own', 'OWN'),
        ('to_one', 'TO_ONE'),
        ('to_many', 'TO_MANY'),
    )

    class Meta:
        name = "_"

    @classmethod
    def _get_fields(cls):
        model = getattr(cls.Meta, 'model', None)
        fields = {}
        if model is None:
            return fields

        model_resource_map = cls.Meta.api.model_resource_map
        options = model._meta
        for field in options.fields:
            if field.rel is None:
                if field.serialize or field.name == 'id':
                    fields[field.name] = {
                        "type": Resource.FIELD_TYPES.OWN,
                        "name": field.name,
                    }
            else:
                if field.rel.multiple:
                    # ForeignKey
                    if field.rel.to in model_resource_map:
                        related_resource = model_resource_map[field.rel.to]
                        fields[related_resource.Meta.name] = {
                            "type": Resource.FIELD_TYPES.TO_ONE,
                            "name": field.name,
                        }

        for related_model, related_resource in model_resource_map.items():
            for field in related_model._meta.fields:
                if field.rel and field.rel.to == model:
                    fields[related_resource.Meta.name_plural] = {
                        "type": Resource.FIELD_TYPES.TO_MANY,
                        "name": field.rel.related_name or
                        "{}_set".format(related_resource.Meta.name)
                    }

        return fields

    @classmethod
    def _get_fields_own(cls):
        return {
            k: v for k, v in cls._get_fields().items()
            if v["type"] == Resource.FIELD_TYPES.OWN
        }

    @classmethod
    def _get_fields_to_one(cls):
        return {
            k: v for k, v in cls._get_fields().items()
            if v["type"] == Resource.FIELD_TYPES.TO_ONE
        }

    @classmethod
    def _get_fields_to_many(cls):
        return {
            k: v for k, v in cls._get_fields().items()
            if v["type"] == Resource.FIELD_TYPES.TO_MANY
        }

    @classmethod
    def get(cls, **kwargs):
        """ Get resource http response.

        :return str: resource

        """
        import json
        model = cls.Meta.model
        data = [
            Serializer.dump_document(
                m,
                fields=cls._get_fields_own(),
                fields_to_one=cls._get_fields_to_one(),
                fields_to_many=cls._get_fields_to_many()
            )
            for m in model.objects.all()
        ]
        response = json.dumps({cls.Meta.name_plural: data})
        return response
