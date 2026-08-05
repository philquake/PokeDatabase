from django.test import TestCase
import lxml.html

# Create your tests here.
class HomePageTest(TestCase):
    def test_home_page_template(self):
        response = self.client.get('/')
        self.assertTemplateUsed(response, 'home.html')

    def test_renders_search_bar(self):
        response = self.client.get('/')
        parsed =lxml.html.fromstring(response.content)
        [form] = parsed.cssselect("form[method=GET]")
        # self.assertEqual(form.get("action"), "/search/")