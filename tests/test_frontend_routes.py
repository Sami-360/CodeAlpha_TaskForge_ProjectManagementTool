import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class FrontendRouteTests(SimpleTestCase):
    def test_root_entry_targets_existing_frontend_pages(self):
        entry = (Path(settings.BASE_DIR) / 'index.html').read_text(encoding='utf-8')
        for target in ('frontend/pages/login.html', 'frontend/pages/dashboard.html'):
            self.assertIn(target, entry)
            self.assertTrue((Path(settings.BASE_DIR) / target).is_file())

    def test_local_page_links_resolve_to_existing_files(self):
        pages = Path(settings.BASE_DIR) / 'frontend' / 'pages'
        for page in pages.glob('*.html'):
            html = page.read_text(encoding='utf-8')
            for href in re.findall(r'href="([^"#]+\.html)(?:\?[^"#]*)?"', html):
                target = (page.parent / href).resolve()
                self.assertTrue(target.is_file(), f'{page.name} links to missing {href}')
