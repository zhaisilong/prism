"""Explicit immutable venue definitions and reusable build policies.

No directory discovery or TeX installation is needed to query this catalog.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
from .paths import PROJECT_DIR, ASSET_DIR
from .catalog_models import (BuildProfile, DocumentRole, SourceReference, TemplateDefinition, relative_path)


@dataclass(frozen=True)
class TemplateCatalog:
    templates: Mapping[str, TemplateDefinition]
    profiles: Mapping[str, BuildProfile]

    def __post_init__(self):
        object.__setattr__(self, "templates", MappingProxyType(dict(self.templates)))
        object.__setattr__(self, "profiles", MappingProxyType(dict(self.profiles)))
        self.choices()

    def choices(self):
        for name, profile in self.profiles.items():
            if not isinstance(name, str) or not name or not isinstance(profile, BuildProfile):
                raise ValueError("Invalid build profile registration")
        names = []
        for alias, record in self.templates.items():
            if not isinstance(record, TemplateDefinition) or record.alias != alias:
                raise ValueError("Invalid template registration")
            if alias in names or record.id in names or alias == record.id:
                raise ValueError("Duplicate Prism template name")
            if record.backend not in self.profiles or not isinstance(self.profiles[record.backend], BuildProfile):
                raise ValueError("Unknown build profile")
            names.extend((alias, record.id))
        return tuple(names)

    def resolve(self, name):
        for alias, record in self.templates.items():
            if name == alias or name == record.id:
                return alias
        raise ValueError(f"unknown template: {name}")

    def article_type(self, name, requested=None):
        record = self.templates[self.resolve(name)]
        if requested is None:
            return record.article_type
        if not isinstance(requested, str) or requested not in record.article_types:
            raise ValueError(f"Unsupported article type for {name}: use a type listed by --list-templates")
        return requested

    def profile(self, name, variant=None):
        alias = self.resolve(name)
        if alias == "nature":
            if variant not in (None, "prism-article", "sn-jnl"):
                raise ValueError("unknown Nature template variant")
            if variant == "sn-jnl":
                return replace(self.profiles["nature"], packages=NATURE_PACKAGES)
        elif variant is not None:
            raise ValueError("template variant is only supported for Nature")
        return self.profiles[self.templates[alias].backend]

    def detail(self, name):
        alias = self.resolve(name)
        record = self.templates[alias]
        profile = self.profile(alias)
        return {
            "schema_version": 1, "alias": alias, "id": record.id, "kind": record.kind,
            "venue": record.venue, "publisher": record.publisher,
            "article_types": list(record.article_types or (record.article_type,)),
            "default_article_type": record.article_type,
            "languages": {"bilingual": {"engines": ["xelatex", "lualatex"] if record.engine == "auto" else ["xelatex"], "default_engine": "auto" if record.engine == "auto" else "xelatex"},
                          "english": {"engines": ["xelatex", "lualatex"] if record.engine == "auto" else ["pdflatex", "xelatex"], "default_engine": record.engine}},
            "bibliography": "bibtex", "description": record.description,
            "required_assets": list(record.required_assets),
            "documents": [{"role": role.role, "path": role.path, "standalone": role.standalone} for role in record.documents],
            "guide_path": record.guide_path, "asset_path": "skills/paper-latex/assets/" + record.directory,
            "capabilities": {"article_type_selection": record.supports_article_type, "official_package_import": profile.source is not None and profile.bundled is None},
            "sources": [{"label": source.label, "url": source.url} for source in record.sources],
        }

    def validate(self, repo_dir=PROJECT_DIR, asset_dir=ASSET_DIR):
        from .catalog_validation import validate_catalog
        return validate_catalog(self, Path(repo_dir), Path(asset_dir))

PRISM_PACKAGES = (
    "iftex.sty", "bookmark.sty", "graphicx.sty", "caption.sty",
    "unicode-math.sty", "texgyretermes-math.otf", "subcaption.sty",
    "siunitx.sty", "ragged2e.sty", "etoolbox.sty", "xurl.sty",
    "enumitem.sty", "booktabs.sty", "tabularx.sty", "longtable.sty",
    "amsmath.sty", "amssymb.sty", "natbib.sty", "fancyhdr.sty", "pdflscape.sty", "placeins.sty",
)
NATURE_PACKAGES = (
    "graphicx.sty", "amsmath.sty", "amssymb.sty", "amsfonts.sty",
    "booktabs.sty", "tabularx.sty", "siunitx.sty", "longtable.sty",
    "setspace.sty", "cuted.sty", "rotating.sty", "threeparttable.sty",
    "appendix.sty", "wrapfig.sty", "amsthm.sty", "fix-cm.sty", "natbib.sty",
    "caption.sty", "subcaption.sty", "pdflscape.sty",
)
NATURE_COMMUNICATIONS_PACKAGES = (
    "article.cls", "geometry.sty", "hyperref.sty", "array.sty", "graphicx.sty", "amsmath.sty", "amssymb.sty",
    "booktabs.sty", "tabularx.sty", "siunitx.sty", "longtable.sty",
    "caption.sty", "subcaption.sty", "pdflscape.sty", "natbib.sty", "unsrt.bst",
)
SCIENCE_PACKAGES = (
    "article.cls", "graphicx.sty", "newtxtext.sty", "newtxmath.sty",
    "url.sty", "amsmath.sty", "amssymb.sty", "booktabs.sty",
    "tabularx.sty", "siunitx.sty", "longtable.sty", "caption.sty",
    "subcaption.sty", "pdflscape.sty", "natbib.sty", "unsrtnat.bst",
)
BIB_PACKAGES = (
    "crop.sty", "graphicx.sty", "caption.sty", "amsmath.sty", "array.sty",
    "color.sty", "xcolor.sty", "amssymb.sty", "flushend.sty", "stfloats.sty",
    "rotating.sty", "chngpage.sty", "totcount.sty", "fix-cm.sty", "footmisc.sty",
    "natbib.sty", "wrapfig.sty", "amsthm.sty", "subfloat.sty", "multirow.sty",
    "footnote.sty", "url.sty", "mathrsfs.sty", "algorithm.sty", "algorithmicx.sty",
    "algpseudocode.sty", "listings.sty", "hyperref.sty", "tikz.sty", "booktabs.sty",
    "tabularx.sty", "siunitx.sty", "longtable.sty", "subcaption.sty", "pdflscape.sty",
    "unsrt.bst",
)
DDT_PACKAGES = (
    "elsarticle.cls", "elsarticle-num.bst", "natbib.sty", "graphicx.sty",
    "amsmath.sty", "amssymb.sty", "booktabs.sty", "tabularx.sty",
    "siunitx.sty", "longtable.sty", "caption.sty", "subcaption.sty",
    "pdflscape.sty",
)
JCIM_PACKAGES = (
    "article.cls", "achemso.sty", "achemso.bst", "xkeyval.sty", "natbib.sty",
    "natmove.sty", "graphicx.sty", "amsmath.sty", "amssymb.sty",
    "booktabs.sty", "tabularx.sty", "siunitx.sty", "longtable.sty",
    "caption.sty", "subcaption.sty", "pdflscape.sty",
)
WILEY_PACKAGES = (
    "article.cls", "ifpdf.sty", "ifxetex.sty", "ifluatex.sty", "mathtools.sty", "bm.sty",
    "graphicx.sty", "tabularx.sty", "textcase.sty", "dashrule.sty", "ragged2e.sty",
    "authblk.sty", "url.sty", "soul.sty", "xpatch.sty", "afterpage.sty", "lineno.sty",
    "mdframed.sty", "tikz.sty", "silence.sty", "microtype.sty", "geometry.sty",
    "alphalph.sty", "scrextend.sty", "titlesec.sty", "footmisc.sty", "fancyhdr.sty",
    "changepage.sty", "environ.sty", "marginnote.sty", "quoting.sty", "enumitem.sty",
    "caption.sty", "threeparttable.sty", "stfloats.sty", "newfloat.sty", "enotez.sty",
    "natbib.sty", "lettrine.sty", "hyperref.sty", "booktabs.sty", "longtable.sty",
    "siunitx.sty", "mhchem.sty", "subcaption.sty", "pdflscape.sty", "amssymb.sty",
)
ADVANCED_SCIENCE_PACKAGES = (
    "article.cls", "geometry.sty", "hyperref.sty", "array.sty", "graphicx.sty",
    "amsmath.sty", "amssymb.sty", "booktabs.sty", "tabularx.sty", "siunitx.sty",
    "longtable.sty", "caption.sty", "subcaption.sty", "pdflscape.sty",
    "natbib.sty", "newfloat.sty", "mhchem.sty",
)


BUILD_PROFILES = MappingProxyType({
    'prism': BuildProfile(
        packages=PRISM_PACKAGES,
        source=None,
        examples=False,
    ),
    'nature': BuildProfile(
        packages=NATURE_COMMUNICATIONS_PACKAGES + ("geometry.sty", "hyperref.sty", "amsfonts.sty", "array.sty"),
        source="nature",
        examples=True,
    ),
    'nature-communications': BuildProfile(
        packages=NATURE_COMMUNICATIONS_PACKAGES,
        source=None,
        examples=True,
    ),
    'jcheminformatics': BuildProfile(
        packages=NATURE_COMMUNICATIONS_PACKAGES + ("lineno.sty", "setspace.sty"),
        source=None,
        examples=True,
    ),
    'science': BuildProfile(
        packages=SCIENCE_PACKAGES,
        source="science",
        examples=True,
    ),
    'oup-numeric': BuildProfile(
        packages=BIB_PACKAGES,
        source="oup-numeric",
        examples=True,
    ),
    'oup-authoryear': BuildProfile(
        packages=BIB_PACKAGES + ("unsrtnat.bst",),
        source="oup-authoryear",
        examples=True,
    ),
    'oup-nar': BuildProfile(
        packages=BIB_PACKAGES + ("geometry.sty",),
        source="oup-numeric",
        examples=True,
        resources=("prism-nar.bst",),
        required_common=("supplementary.tex", "graphical_abstract.tex", "references.bib", "prism-nar.bst"),
    ),
    'wiley-overleaf': BuildProfile(
        packages=WILEY_PACKAGES,
        source=None,
        examples=True,
        bundled=("wiley-overleaf", {"wiley-article.cls": "wiley-article.cls"}),
        shared_assets=("prism-wiley-article.cls",),
        resources=('prism-wiley-article.cls', 'prism-angew.bst', 'wiley-template-NOTICE.md', 'wiley-template-LICENSE.txt'),
        required_common=("supplementary.tex", "references.bib", "prism-angew.bst", "NOTICE.md"),
        xelatex_packages=(
            "fontspec.sty", "unicode-math.sty", "texgyretermes-regular.otf", "texgyretermes-bold.otf",
            "texgyretermes-italic.otf", "texgyretermes-bolditalic.otf", "XITSMath-Regular.otf",
            "XITSMath-Bold.otf", "Lato-Regular.ttf", "Lato-Bold.ttf", "Lato-Italic.ttf",
            "Lato-BoldItalic.ttf", "Lato-Black.ttf",
        ),
        pdftex_packages=("tgtermes.sty", "lato.sty", "stix.sty"),
    ),
    'advanced-science': BuildProfile(
        packages=ADVANCED_SCIENCE_PACKAGES,
        source=None,
        examples=True,
        shared_assets=("prism-wiley-numeric.bst",),
        resources=("prism-wiley-numeric.bst",),
        required_common=("supplementary.tex", "references.bib", "NOTICE.md"),
    ),
    'ddt': BuildProfile(
        packages=DDT_PACKAGES,
        source=None,
        examples=True,
    ),
    'acs': BuildProfile(
        packages=JCIM_PACKAGES,
        source=None,
        examples=True,
        isolate_cwd=True,
    ),
    'acs-medicinal-chemistry': BuildProfile(
        packages=JCIM_PACKAGES + ("setspace.sty", "newfloat.sty", "mhchem.sty"),
        source=None,
        examples=True,
        isolate_cwd=True,
        required_common=("supplementary.tex", "references.bib", "NOTICE.md"),
    ),
    'elsarticle-numeric': BuildProfile(
        packages=DDT_PACKAGES + ("newfloat.sty", "mhchem.sty"),
        source=None,
        examples=True,
        required_common=("supplementary.tex", "references.bib", "NOTICE.md",
                         "graphical_abstract.tex", "highlights.txt"),
    ),
})

TEMPLATES = MappingProxyType({
    'prism': TemplateDefinition(
        alias='prism',
        id='generic/prism',
        kind='generic',
        venue='Prism',
        publisher=None,
        article_type='manuscript',
        backend='prism',
        directory='paper-template',
        engine='auto',
        description='Prism manuscript; English / Chinese; XeLaTeX or LuaLaTeX (default)',
        guide_path='docs/templates/prism.md',
        required_assets=('prism-paper.sty', 'sections/abstract.tex', 'sections/introduction.tex', 'sections/methods.tex', 'sections/results.tex', 'sections/discussion.tex', 'sections/appendix.tex'),
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(),
    ),
    'nature': TemplateDefinition(
        alias='nature',
        id='family/nature-nmi',
        kind='family',
        venue='Nature / NMI draft',
        publisher='Springer Nature',
        article_type='research',
        backend='nature',
        directory='nature-template',
        engine='pdflatex',
        description='Nature / NMI manuscript and supplementary information; bilingual / English',
        guide_path='docs/templates/nature.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Springer Nature author support', 'https://www.springernature.com/gp/authors/campaigns/latex-author-support'),
        ),
    ),
    'nature-communications': TemplateDefinition(
        alias='nature-communications',
        id='journal/nature-communications',
        kind='journal',
        venue='Nature Communications',
        publisher='Springer Nature',
        article_type='research',
        backend='nature-communications',
        directory='nature-communications-template',
        engine='pdflatex',
        description='Nature Communications research article and supplementary information; bilingual / English',
        guide_path='docs/templates/nature-communications.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://www.nature.com/ncomms/submit/how-to-submit'),
        ),
    ),
    'jcheminformatics': TemplateDefinition(
        alias='jcheminformatics',
        id='journal/journal-of-cheminformatics',
        kind='journal',
        venue='Journal of Cheminformatics',
        publisher='Springer Nature',
        article_type='research',
        backend='jcheminformatics',
        directory='jcheminformatics-template',
        engine='pdflatex',
        description='Journal of Cheminformatics research article and supplementary information; bilingual / English',
        guide_path='docs/templates/jcheminformatics.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://link.springer.com/journal/13321/submission-guidelines'),
        ),
    ),
    'science-advances': TemplateDefinition(
        alias='science-advances',
        id='journal/science-advances',
        kind='journal',
        venue='Science Advances',
        publisher='AAAS',
        article_type='research',
        backend='science',
        directory='science-advances-template',
        engine='pdflatex',
        description='Science Advances research article and combined supplementary material; bilingual / English',
        guide_path='docs/templates/science-advances.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'main.tex', False),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Science-family LaTeX', 'https://www.science.org/content/page/preparing-manuscripts-using-latex'),
        ),
    ),
    'bib': TemplateDefinition(
        alias='bib',
        id='journal/briefings-in-bioinformatics',
        kind='journal',
        venue='Briefings in Bioinformatics',
        publisher='Oxford University Press',
        article_type='manuscript',
        backend='oup-numeric',
        directory='bib-template',
        engine='pdflatex',
        description='Briefings in Bioinformatics (OUP); bilingual / English',
        guide_path='docs/templates/bib.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://academic.oup.com/bib/pages/author-guidelines'),
        ),
    ),
    'ddt': TemplateDefinition(
        alias='ddt',
        id='journal/drug-discovery-today',
        kind='journal',
        venue='Drug Discovery Today',
        publisher='Elsevier',
        article_type='review',
        backend='ddt',
        directory='ddt-template',
        engine='pdflatex',
        description='Drug Discovery Today narrative review (Elsevier); bilingual / English',
        guide_path='docs/templates/ddt.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://www.sciencedirect.com/journal/drug-discovery-today/publish/guide-for-authors'),
        ),
    ),
    'jcim': TemplateDefinition(
        alias='jcim',
        id='journal/jcim',
        kind='journal',
        venue='Journal of Chemical Information and Modeling',
        publisher='ACS',
        article_type='research',
        backend='acs',
        directory='jcim-template',
        engine='pdflatex',
        description='Journal of Chemical Information and Modeling research article (ACS); bilingual / English',
        guide_path='docs/templates/jcim.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('toc_graphic', 'main.tex', False),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://researcher-resources.acs.org/publish/author_guidelines?coden=jcisd8'),
        ),
    ),
    'jacs': TemplateDefinition(
        alias='jacs',
        id='journal/jacs',
        kind='journal',
        venue='Journal of the American Chemical Society',
        publisher='ACS',
        article_type='research',
        backend='acs',
        directory='jacs-template',
        engine='pdflatex',
        description='Journal of the American Chemical Society research article (ACS); bilingual / English',
        guide_path='docs/templates/jacs.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('toc_graphic', 'main.tex', False),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://researcher-resources.acs.org/publish/author_guidelines?coden=jacsat'),
        ),
    ),
    'chemrev': TemplateDefinition(
        alias='chemrev',
        id='journal/chemical-reviews',
        kind='journal',
        venue='Chemical Reviews',
        publisher='ACS',
        article_type='review',
        backend='acs',
        directory='chemical-reviews-template',
        engine='pdflatex',
        description='Chemical Reviews regular Review; Prism-maintained ACS draft; bilingual / English',
        guide_path='docs/templates/chemrev.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('toc_graphic', 'main.tex', False),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://researcher-resources.acs.org/publish/author_guidelines?coden=chreay'),
        ),
    ),
    'bioinformatics': TemplateDefinition(
        alias='bioinformatics',
        id='journal/bioinformatics',
        kind='journal',
        venue='Bioinformatics',
        publisher='Oxford University Press',
        article_type='original',
        backend='oup-authoryear',
        directory='bioinformatics-template',
        engine='pdflatex',
        description='Bioinformatics original paper (OUP); bilingual / English',
        guide_path='docs/templates/bioinformatics.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://academic.oup.com/bioinformatics/pages/author-guidelines'),
        ),
    ),
    'nar': TemplateDefinition(
        alias='nar',
        id='journal/nucleic-acids-research',
        kind='journal',
        venue='Nucleic Acids Research',
        publisher='Oxford University Press',
        article_type='research',
        article_types=('research', 'database', 'web-server'),
        backend='oup-nar',
        directory='nar-template',
        engine='pdflatex',
        description='NAR research, Database and Web Server manuscripts (OUP Modern Large); bilingual / English',
        guide_path='docs/templates/nar.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('graphical_abstract', 'graphical_abstract.tex', True),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://academic.oup.com/nar/pages/author-guidelines'),
        ),
    ),
    'angew': TemplateDefinition(
        alias='angew',
        id='journal/angewandte-chemie-international-edition',
        kind='journal',
        venue='Angewandte Chemie International Edition',
        publisher='Wiley-VCH',
        article_type='research',
        article_types=('research', 'communication', 'review', 'minireview'),
        backend='wiley-overleaf',
        directory='angew-template',
        engine='pdflatex',
        description='Angew research, communication, review and minireview drafts; Prism-maintained Wiley derivative; bilingual / English',
        guide_path='docs/templates/angew.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('toc_graphic', 'main.tex', False),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://onlinelibrary.wiley.com/page/journal/15213773/homepage/notice-to-authors'),
        ),
    ),
    'advanced-science': TemplateDefinition(
        alias='advanced-science',
        id='journal/advanced-science',
        kind='journal',
        venue='Advanced Science',
        publisher='Wiley-VCH',
        article_type='research',
        article_types=('research', 'review', 'perspective'),
        backend='advanced-science',
        directory='advanced-science-template',
        engine='pdflatex',
        description='Advanced Science research, review and perspective; Prism-maintained article drafts; bilingual / English',
        guide_path='docs/templates/advanced-science.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('toc_graphic', 'main.tex', False),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://advanced.onlinelibrary.wiley.com/hub/journal/21983844/author-guidelines'),
        ),
    ),
    'jmc': TemplateDefinition(
        alias='jmc',
        id='journal/journal-of-medicinal-chemistry',
        kind='journal',
        venue='Journal of Medicinal Chemistry',
        publisher='ACS',
        article_type='research',
        article_types=('research', 'perspective'),
        backend='acs-medicinal-chemistry',
        directory='jmc-template',
        engine='pdflatex',
        description='Journal of Medicinal Chemistry research and perspective drafts; bilingual / English',
        guide_path='docs/templates/jmc.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('toc_graphic', 'main.tex', False),
        ),
        sources=(
            SourceReference('Author guidelines', 'https://researcher-resources.acs.org/publish/author_guidelines?coden=jmcmar'),
            SourceReference('ACS TOC graphics', 'https://pubsapp.acs.org/paragonplus/submission/toc_abstract_graphics_guidelines.pdf'),
        ),
    ),
    'ejmc': TemplateDefinition(
        alias='ejmc',
        id='journal/european-journal-of-medicinal-chemistry',
        kind='journal',
        venue='European Journal of Medicinal Chemistry',
        publisher='Elsevier',
        article_type='research',
        article_types=('research', 'review'),
        backend='elsarticle-numeric',
        directory='ejmc-template',
        engine='pdflatex',
        description='European Journal of Medicinal Chemistry research and review drafts; bilingual / English',
        guide_path='docs/templates/ejmc.md',
        documents=(
            DocumentRole('main', 'main.tex', True),
            DocumentRole('supplementary', 'supplementary.tex', True),
            DocumentRole('examples', 'examples.tex', True),
            DocumentRole('graphical_abstract', 'graphical_abstract.tex', True),
        ),
        sources=(
            SourceReference('Journal scope', 'https://shop.elsevier.com/journals/european-journal-of-medicinal-chemistry/0223-5234'),
            SourceReference('Author guidelines', 'https://www.sciencedirect.com/journal/european-journal-of-medicinal-chemistry/publish/guide-for-authors'),
            SourceReference('Elsevier LaTeX', 'https://www.elsevier.com/researcher/author/policies-and-guidelines/latex-instructions'),
        ),
    ),
})

CATALOG = TemplateCatalog(TEMPLATES, BUILD_PROFILES)

def template_choices() -> tuple[str, ...]:
    return CATALOG.choices()

def resolve_template(name: str) -> str:
    return CATALOG.resolve(name)

def article_type_choices() -> tuple[str, ...]:
    """CLI choices come only from templates that expose content selection."""
    template_choices()
    return tuple(dict.fromkeys(value for record in TEMPLATES.values()
                               for value in record.get("article_types", ())))

def format_template_catalog(group_by: str = "none") -> str:
    """Render the one registry; retain the original flat command's output."""
    template_choices()
    if group_by == "none":
        rows = []
        for alias, record in TEMPLATES.items():
            publisher = record["publisher"] or "Prism"
            articles = f"; article types: {', '.join(record['article_types'])}" if record.get("article_types") else ""
            rows.append(f"{alias}: {record['description']} [ID: {record['id']}; type: {record['kind']}; publisher: {publisher}{articles}]")
        return "\n".join(rows)
    if group_by != "publisher":
        raise ValueError("Unsupported template grouping; use none or publisher")
    groups: dict[str, list[tuple[str, TemplateDefinition]]] = {}
    for alias, record in TEMPLATES.items():
        label = "Prism / 通用" if record["kind"] == "generic" else record["publisher"] or "未指定出版社"
        groups.setdefault(label, []).append((alias, record))
    rows = []
    for label in sorted(groups, key=lambda value: (value != "Prism / 通用", value.casefold())):
        if rows:
            rows.append("")
        rows.append(label)
        for alias, record in sorted(groups[label], key=lambda item: (item[1]["venue"].casefold(), item[0])):
            rows.append(f"  {alias}: {record['venue']} [ID: {record['id']}]")
            if record.get("article_types"):
                options = ", ".join(record["article_types"])
                rows.append(f"    --article-type: {options} (default: {record['article_type']})")
            else:
                rows.append(f"    用途: {record['description']}")
    return "\n".join(rows)

def template_profile(template: str, variant: str | None = None) -> BuildProfile:
    return CATALOG.profile(template, variant)

def template_isolated_build(template: str | None) -> bool:
    return bool(template and template_profile(template).get("isolate_cwd", False))

def template_article_type(template: str, requested: str | None = None) -> str:
    return CATALOG.article_type(template, requested)

def template_engine(template: str | None, requested: str, language: str | None = None) -> str:
    if language not in (None, "bilingual", "english"):
        raise SystemExit("Invalid template language; use bilingual or english.")
    alias = resolve_template(template) if template else None
    if alias and TEMPLATES[alias]["backend"] == "prism" and requested == "pdflatex":
        raise SystemExit("The prism template requires XeLaTeX or LuaLaTeX; use --engine auto, xelatex, or lualatex.")
    if alias and TEMPLATES[alias]["engine"] == "pdflatex":
        if language == "bilingual":
            if requested not in ("auto", "xelatex"):
                raise SystemExit(f"The bilingual {alias} template requires XeLaTeX; use --engine auto or xelatex.")
            return "xelatex"
        if requested in ("auto", "pdflatex"):
            return "pdflatex"
        if requested == "xelatex":
            return "xelatex"
        raise SystemExit(f"The {alias} template supports pdfLaTeX or XeLaTeX; use --engine auto, pdflatex, or xelatex.")
    return requested

def template_packages(
    template: str | None, engine: str, variant: str | None = None,
    language: str | None = None,
) -> tuple[str, ...]:
    engine = template_engine(template, engine, language)
    if template:
        profile = template_profile(template, variant)
        packages = profile["packages"]
        packages += profile.xelatex_packages if engine == "xelatex" else profile.pdftex_packages
        return packages
    # Existing, unmarked projects can explicitly request pdfLaTeX too.
    if engine == "pdflatex":
        return ("graphicx.sty", "amsmath.sty", "amssymb.sty", "natbib.sty")
    return PRISM_PACKAGES
