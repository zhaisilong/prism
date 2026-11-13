"""RSC Advances offline starter and real bibliography contracts."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from unittest import mock
import urllib.request
import xml.etree.ElementTree as ET

from prism_test_support import ROOT, TemplateSupport, require_tex
sys.path.insert(0, str(ROOT / 'scripts/lib'))
from prism_latex import templates
from prism_latex.catalog import CATALOG


class RscAdvancesTests(TemplateSupport, unittest.TestCase):
    default_template = 'rsc-advances'
    canonical = 'journal/rsc-advances'

    def test_catalog_and_offline_initialization(self):
        detail = CATALOG.detail(self.default_template)
        self.assertEqual(detail['id'], self.canonical)
        self.assertEqual(detail['publisher'], 'Royal Society of Chemistry')
        self.assertEqual(detail['article_types'], ['research', 'review'])
        self.assertEqual(detail['default_article_type'], 'research')
        self.assertFalse(detail['capabilities']['official_package_import'])
        with mock.patch.object(urllib.request, 'urlopen', side_effect=AssertionError('network')) as fetch:
            for kind in ('research', 'review'):
                for language, engine in (('bilingual', 'xelatex'), ('english', 'pdflatex')):
                    project = self.root / '研究项目 with spaces' / kind / language
                    self.initialize(project, template=self.canonical, article_type=kind, language=language)
                    meta = json.loads((project / 'prism-template.json').read_text())
                    self.assertEqual((meta['schema_version'], meta['template_id'], meta['article_type'], meta['engine']),
                                     (1, self.canonical, kind, engine))
                    self.assertTrue((project / 'supplementary.tex').is_file())
                    self.assertTrue((project / 'examples.tex').is_file())
                    self.assert_clean(project)
            fetch.assert_not_called()
        env = dict(self.env, PATH='')
        listing = self.cli('--list-templates', '--group-by', 'publisher', env=env)
        self.assert_success(listing)
        self.assertIn('Royal Society of Chemistry', listing.stdout)
        self.assertIn(self.canonical, listing.stdout)
        deps = self.cli('--check-deps', '--template', self.default_template, env=env)
        self.assertNotEqual(deps.returncode, 0)
        self.assertIn('rsc.bst: MISSING', deps.stdout)

    def test_invalid_options_and_force_backup(self):
        project = self.root / '已有稿件'
        self.initialize(project)
        (project / 'local.txt').write_text('synthetic author content')
        before = self.inventory(project)
        for option in (('--article-type', 'comment'), ('--language', 'unknown'),
                       ('--template-source', self.root / 'unused.zip')):
            result = self.cli('--init', project, '--force', '--template', self.default_template, *option)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.inventory(project), before)
            self.assertFalse(project.with_name(project.name + '.backup').exists())
        self.assertNotEqual(self.cli('--init', project, '--template', self.default_template).returncode, 0)
        self.initialize(project, article_type='review', force=True)
        self.assertEqual(self.inventory(project.with_name(project.name + '.backup')), before)
        self.assertEqual(templates.template_article_type_for_project(project), 'review')

    def test_missing_assets_leave_existing_target_unchanged(self):
        assets = self.root / 'assets'
        assets.mkdir()
        shutil.copytree(templates.ASSET_DIR / 'rsc-advances-template', assets / 'rsc-advances-template')
        (assets / 'paper-template').mkdir()
        shutil.copy2(templates.ASSET_DIR / 'paper-template/examples.tex', assets / 'paper-template/examples.tex')
        shutil.copy2(templates.ASSET_DIR / 'prism-cjk.sty', assets / 'prism-cjk.sty')
        target = self.root / 'preserve'
        target.mkdir()
        (target / 'keep.txt').write_text('synthetic')
        before = self.inventory(target)
        for name in ('common/supplementary.tex', 'common/references.bib', 'common/NOTICE.md', 'review/main.tex'):
            path = assets / 'rsc-advances-template' / name
            data = path.read_bytes()
            path.unlink()
            try:
                with mock.patch.object(templates, 'ASSET_DIR', assets):
                    with self.assertRaisesRegex(SystemExit, 'missing'):
                        self.initialize(target, article_type='review', force=True)
                self.assertEqual(self.inventory(target), before)
                self.assertFalse(target.with_name(target.name + '.backup').exists())
            finally:
                path.write_bytes(data)

    def test_real_rsc_citations_and_failure_preserve_pdf(self):
        require_tex(self, ('rsc.sty', 'rsc.bst', 'mhchem.sty'))
        if not shutil.which('pdftohtml'):
            self.skipTest('DOI link check requires pdftohtml')
        project = self.root / '引文'
        self.initialize(project, language='english')
        main = (project / 'main.tex').read_text()
        preamble = main.split(r'\begin{document}', 1)[0]
        style = re.search(r'\\bibliographystyle\{[^}]+\}', main).group()
        document = (preamble + '\n' + r'\begin{document}' + '\n'
                    + r'FirstMarker\cite{zulu}; SecondMarker\cite{alpha}.' + '\n'
                    + style + '\n' + r'\bibliography{fixture}' + '\n' + r'\end{document}' + '\n')
        fixture = project / 'citation-check.tex'
        fixture.write_text(document)
        (project / 'fixture.bib').write_text('\n'.join(
            '@article{' + key + ', author={Example, Alice}, title={' + title
            + '}, journal={Synthetic Journal}, year={2026}, volume={2}, pages={11--19},'
            + ' doi={10.0000/prism-rsc-' + key + '}}'
            for key, title in (('alpha', 'Complete Alpha Article Title'), ('zulu', 'Complete Zulu Article Title'))))
        # The source directory must never shadow the generated control file.
        conflict = project / 'rsc-citation-check.bib'
        control = '@Control{rsc-control, ctrl-use-title="no", ctrl-use-doi-all="no"}'
        conflict.write_text(control)
        args = (project, '--main', fixture.name, '--strict', '--no-build-script')
        self.assert_success(self.cli(*args))
        pdf = fixture.with_suffix('.pdf')
        text = ' '.join(self.text_of(pdf, '-raw').replace('-\n', '').split())
        self.assertRegex(text, r'FirstMarker;\s*1\s*SecondMarker\.\s*2')
        bbox = subprocess.run(['pdftotext', '-bbox', str(pdf), '-'], capture_output=True, text=True, check=True).stdout
        words = list(ET.fromstring(bbox).iter('{http://www.w3.org/1999/xhtml}word'))
        marker = next(i for i, word in enumerate(words) if word.text == 'FirstMarker;')
        self.assertEqual(words[marker + 1].text, '1')
        self.assertLess(float(words[marker + 1].attrib['yMax']), float(words[marker].attrib['yMax']))
        self.assertLess(text.casefold().index('complete zulu article title'),
                        text.casefold().index('complete alpha article title'))
        html = subprocess.run(['pdftohtml', '-stdout', '-i', '-noframes', str(pdf)],
                              capture_output=True, text=True, check=True, timeout=30).stdout
        for key in ('alpha', 'zulu'):
            self.assertIn('href="http://dx.doi.org/10.0000/prism-rsc-' + key + '"', html)
        previous = pdf.read_bytes()
        fixture.write_text(document.replace(r'\end{document}', r'\UndefinedSyntheticFixture' + '\n' + r'\end{document}'))
        self.assertNotEqual(self.cli(*args).returncode, 0)
        self.assertEqual(pdf.read_bytes(), previous)
        self.assert_clean(project)
        self.assertEqual(conflict.read_text(), control)
        self.assertEqual([p.name for p in project.glob('rsc-*.bib')], [conflict.name])


if __name__ == '__main__':
    unittest.main()
