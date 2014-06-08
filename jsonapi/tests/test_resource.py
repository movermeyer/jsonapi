from django.test import TestCase
import json

from django.test import Client
from mixer.backend.django import mixer

from jsonapi.tests.testapp.models import Author
from jsonapi.tests.testapp.resources import AuthorResource


class TestResource(TestCase):
    def setUp(self):
        pass

    def test_django_resource_name(self):
        self.assertEqual(AuthorResource.Meta.name, 'author')
        self.assertEqual(AuthorResource.Meta.name_plural, 'authors')

    def test_resource_get_empty(self):
        c = Client()
        response = c.get(
            '/api/author/',
            content_type='application/vnd.api+json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf8'))
        data_expected = {
            "authors": []
        }
        self.assertEqual(data, data_expected)

    def test_resource_get(self):
        author = mixer.blend(Author)
        c = Client()
        response = c.get(
            '/api/author/',
            content_type='application/vnd.api+json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf8'))
        data_expected = {
            "authors": [{
                "id": author.id
            }]
        }
        self.assertEqual(data, data_expected)
