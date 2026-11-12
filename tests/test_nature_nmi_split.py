"""Nature/NMI identity, isolation and build contracts using synthetic projects."""
from __future__ import annotations

import json
import shutil
import sys
import unittest
import urllib.request
from unittest import mock

from prism_test_support import ROOT, TemplateSupport, require_tex
sys.path.insert(0, str(ROOT / 'scripts/lib'))
from prism_latex import templates
from prism_latex.catalog import CATALOG


class NatureNmiSplitTests(TemplateSupport, unittest.TestCase):
    def test_catalog_and_offline_initialization(self):
        self.assertEqual(CATALOG.resolve('family/nature-nmi'), 'nature')
        self.assertEqual(CATALOG.detail('nature')['id'], 'journal/nature')
        self.assertEqual(CATALOG.detail('nmi')['id'], 'journal/nature-machine-intelligence')
        self.assertEqual(CATALOG.detail('nmi')['article_types'], ['article', 'analysis', 'review'])
        env = dict(self.env, PATH='')
        listing = self.cli('--list-templates', '--group-by', 'publisher', env=env)
        self.assert_success(listing)
        self.assertIn('  nature: Nature [ID: journal/nature]', listing.stdout)
        self.assertIn('  nmi: Nature Machine Intelligence [ID: journal/nature-machine-intelligence]', listing.stdout)
        with mock.patch.object(urllib.request, 'urlopen', side_effect=AssertionError('network')) as fetch:
            for language in ('english', 'bilingual'):
                for kind in ('article', 'analysis', 'review'):
                    with self.subTest(language=language, kind=kind):
                        project = self.root / '中文 路径' / language / kind
                        self.initialize(project, template='nmi', article_type=kind, language=language)
                        meta = json.loads((project / templates.METADATA_NAME).read_text())
                        self.assertEqual((meta['schema_version'], meta['template_id'], meta['article_type']),
                                         (1, 'journal/nature-machine-intelligence', kind))
                        self.assertEqual(meta['engine'], 'xelatex' if language == 'bilingual' else 'pdflatex')
                        for name in ('main.tex', 'supplementary.tex', 'examples.tex'):
                            self.assertEqual(r'\usepackage{prism-cjk}' in (project/name).read_text(), language == 'bilingual')
                        source = (project/'main.tex').read_text()
                        if kind in ('article', 'analysis'):
                            self.assertIn(r'\section{Results}', source)
                            self.assertIn(r'\section{Discussion}', source)
                            self.assertIn(r'\section{Methods}', source)
                        else:
                            self.assertIn(r'\section{Critical comparison}', source)
                        self.assert_clean(project)
        fetch.assert_not_called()

    def test_legacy_metadata_stays_unchanged(self):
        project = self.root / 'legacy'; project.mkdir()
        path = project / templates.METADATA_NAME
        for extra, expected in (({}, 'sn-jnl'), ({'variant': 'sn-jnl'}, 'sn-jnl'),
                                ({'variant': 'prism-article'}, 'prism-article')):
            meta = dict(schema_version=1, template='nature', template_id='family/nature-nmi', **extra)
            original = json.dumps(meta).encode(); path.write_bytes(original)
            self.assertEqual(templates.template_for_project(project), 'nature')
            self.assertEqual(templates.template_variant_for_project(project), expected)
            self.assertEqual(path.read_bytes(), original)
        self.assertEqual(templates.template_resources('nature', 'sn-jnl'), ('sn-jnl.cls', 'sn-nature.bst'))

    def test_legacy_cli_id_routes_official_local_zip(self):
        from prism_latex import paper
        source = self.root/'official.zip'; source.write_bytes(b'synthetic archive')
        target = self.root/'official'
        args = paper.parser().parse_args(['--init', str(target), '--template', 'family/nature-nmi',
                                          '--template-source', str(source)])
        members = {'sn-jnl.cls': b'synthetic class', 'sn-nature.bst': b'synthetic style'}
        with mock.patch.object(templates, 'nature_package', return_value=(b'synthetic archive', members)) as read:
            templates.initialize(target, False, args.template, source, language='english')
        read.assert_called_once_with(source)
        metadata = json.loads((target/templates.METADATA_NAME).read_text())
        self.assertEqual((metadata['template'], metadata['template_id'], metadata['variant']),
                         ('nature', 'journal/nature', 'sn-jnl'))
        self.assertEqual((target/'sn-jnl.cls').read_bytes(), members['sn-jnl.cls'])

    def test_invalid_import_and_force_backup(self):
        project = self.root/'existing'
        self.initialize(project, template='nmi')
        (project/'author.txt').write_text('synthetic content')
        before = self.inventory(project)
        for args in (('--template-source', self.root/'missing.zip'), ('--article-type', 'resource'),
                     ('--engine', 'lualatex')):
            result = self.cli('--init', project, '--template', 'nmi', '--force', *args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.inventory(project), before)
            self.assertFalse(project.with_name(project.name+'.backup').exists())
        self.initialize(project, template='nmi', article_type='review', force=True)
        self.assertEqual(self.inventory(project.with_name(project.name+'.backup')), before)

    def test_acs_starters_distinguish_chemistry_and_informatics(self):
        for language in ('english', 'bilingual'):
            sources = {}
            for alias in ('jacs', 'jcim'):
                project = self.root/'ACS 论文'/language/alias
                self.initialize(project, template=alias, language=language)
                sources[alias] = (project/'main.tex').read_text()
                self.assertEqual(r'\usepackage{prism-cjk}' in sources[alias], language == 'bilingual')
            self.assertNotEqual(sources['jacs'], sources['jcim'])
            self.assertIn(r'\section{Experimental}', sources['jacs'])
            self.assertIn(r'\subsection{Data curation and representation}', sources['jcim'])
            self.assertIn(r'\subsection{Methods, comparison and validation}', sources['jcim'])
            self.assertIn(r'\section*{Data and Code Availability}', sources['jcim'])

    def test_real_builds_and_failure_preservation(self):
        require_tex(self, ('xeCJK.sty', 'FandolSong-Regular.otf', 'natbib.sty', 'unsrt.bst'))
        for template, kinds in (('nature', (None,)), ('nmi', ('article', 'analysis', 'review'))):
            for language in ('english', 'bilingual'):
                for kind in kinds:
                    with self.subTest(template=template, language=language, kind=kind):
                        project = self.root / '构建 论文' / template / language / (kind or 'default')
                        self.initialize(project, template=template, article_type=kind, language=language)
                        self.assert_success(self.cli(project, '--strict', timeout=300))
                        mainpdf = project/'main.pdf'; oldpdf = mainpdf.read_bytes()
                        self.assertIn('Wilkinson', self.text_of(mainpdf))
                        rebuild = project/'prism-build.sh'; oldscript = rebuild.read_bytes()
                        self.assert_success(self.cli(project, '--main', 'supplementary.tex', '--strict', '--no-build-script', timeout=300))
                        self.assertEqual(rebuild.read_bytes(), oldscript)
                        self.assertTrue((project/'supplementary.pdf').read_bytes().startswith(b'%PDF-'))
                        main = project/'main.tex'; original = main.read_text()
                        main.write_text(original.replace(r'\end{document}', r'\UndefinedSyntheticFixture'+'\n'+r'\end{document}'))
                        self.assertNotEqual(self.cli(project, '--strict', timeout=300).returncode, 0)
                        self.assertEqual(mainpdf.read_bytes(), oldpdf)
                        self.assertEqual(rebuild.read_bytes(), oldscript)
                        self.assert_clean(project)


if __name__ == '__main__':
    unittest.main()
