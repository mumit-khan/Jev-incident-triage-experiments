"""Render repository study documents as a readable article; no inference."""
from html import escape
import math
from pathlib import Path
import re
from string import Template
from urllib.parse import parse_qs, urlencode, urlparse

from markdown_it import MarkdownIt

DOCUMENTS = {
    'overview': 'docs/experiment-overview.md', 'dataset-card': 'docs/dataset-card.md',
    'evaluation-plan': 'docs/evaluation-plan.md', 'performance-review': 'docs/performance-review.md',
    'policy': 'docs/policy.md', 'samples': 'docs/samples.md', 'learning-guide': 'docs/learning-guide.md',
    'observatory': 'docs/observatory.md', 'verification': 'docs/verification.md',
    'run-bundle': 'docs/run-bundle.md', 'handoff': 'HANDOFF.md', 'readme': 'README.md',
}
CHAPTERS = {'overview', 'data', 'models', 'transform', 'results', 'cases', 'sandbox', 'next'}
DEFAULT_RETURN = '/explorer?split=validation&case=NS-b073aba91088&model=jev_focused&field=initial_owner&view=evidence#overview'


def return_path(value):
    """Only a relative walkthrough URL can become the return action."""
    value = value or ''
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or parsed.path != '/explorer' or '\\' in value or len(value) > 4096:
        return DEFAULT_RETURN
    if parsed.fragment and parsed.fragment not in CHAPTERS:
        return DEFAULT_RETURN
    return value


def slug(text):
    text = re.sub(r'[^\w\s-]', '', text.casefold())
    return re.sub(r'[-\s]+', '-', text).strip('-') or 'section'


def render_study(study, params):
    document = params.get('doc', 'overview')
    if document not in DOCUMENTS:
        raise ValueError('Unknown study document.')
    source = (study.root / DOCUMENTS[document]).read_text()
    back = return_path(params.get('return', ''))
    current = {k: v[0] for k, v in parse_qs(urlparse(back).query).items()}
    model = current.get('model', 'jev_focused')
    if model not in {'baseline', 'ml', 'ml_structured', 'jev', 'jev_focused'}:
        model = 'jev_focused'
    identifiers = {identifier: split for split, rows in study.records.items() for identifier in rows}

    def explore(chapter, identifier=None, split=None):
        query = {k: v for k, v in current.items() if k in {'split', 'case', 'model', 'field', 'view'}}
        if identifier:
            query.update(split=split or identifiers[identifier], case=identifier, model=model,
                         field='initial_owner', view='evidence')
        return '/explorer?' + urlencode(query) + '#' + chapter

    def reader_link(href):
        parsed = urlparse(href)
        if not parsed.scheme and not parsed.netloc:
            if href.startswith('#'):
                return '#section-' + parsed.fragment.removeprefix('section-')
            for key, path in DOCUMENTS.items():
                if parsed.path in {path, Path(path).name, '../' + path, '../' + Path(path).name}:
                    query = {'return': back}
                    if key != 'overview':
                        query['doc'] = key
                    return '/study?' + urlencode(query) + ('#section-' + parsed.fragment if parsed.fragment else '')
            if parsed.path.endswith('AGENTS.md'):
                return 'https://github.com/mumit/Jev-incident-triage-experiments/blob/main/AGENTS.md'
        if parsed.hostname in {'127.0.0.1', 'localhost'}:
            query = parse_qs(parsed.query)
            identifier = query.get('case', [None])[0]
            if identifier in identifiers:
                return explore('cases', identifier)
            if parsed.path in {'/', '/explorer', '/study', '/study.md'}:
                return parsed.path + ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')
        return href

    md = MarkdownIt('js-default')
    tokens = md.parse(source)
    headings, used = [], set()
    title = 'Study overview'
    for i, token in enumerate(tokens):
        if token.type == 'heading_open':
            label = tokens[i + 1].content
            anchor = 'section-' + slug(label)
            candidate, suffix = anchor, 2
            while anchor in used:
                anchor = candidate + '-' + str(suffix)
                suffix += 1
            used.add(anchor)
            token.attrSet('id', anchor)
            if token.tag == 'h1':
                title = label.removeprefix('Northstar Telecom: ')
                title = title[:1].upper() + title[1:]
            elif token.tag in {'h2', 'h3'}:
                headings.append((token.tag, label, anchor))
        for child in token.children or []:
            if child.type == 'link_open':
                href = reader_link(child.attrGet('href') or '')
                child.attrSet('href', href)
                if href.startswith(('https://', 'http://')):
                    child.attrSet('target', '_blank')
                    child.attrSet('rel', 'noopener noreferrer')

    def inline_code(renderer, row, index, options, env):
        content = row[index].content
        code = '<code>' + escape(content) + '</code>'
        if content in identifiers:
            return f'<a class="packet-link" href="{escape(explore("cases", content), quote=True)}" title="Inspect this case in the workbench">{code}<span aria-hidden="true"> ↗</span></a>'
        return code

    def fence(renderer, row, index, options, env):
        token = row[index]
        language = token.info.split()[0] if token.info else 'text'
        count = len(token.content.splitlines())
        label = 'JSON input' if language == 'json' else 'Code example'
        return (f'<details class="code-example" {"open" if count <= 24 else ""}>'
                f'<summary><span>{label}</span><span class="code-meta">{escape(language.upper())} · {count} lines</span></summary>'
                '<div class="code-actions"><button type="button" data-copy-code>Copy code</button></div>'
                f'<pre tabindex="0"><code class="language-{escape(language, quote=True)}">{escape(token.content)}</code></pre></details>\n')

    md.add_render_rule('code_inline', inline_code)
    md.add_render_rule('fence', fence)
    cues = {
        'Synthetic data': ('Explore families and packets', explore('data')),
        'First experiment: establish the comparison': ('Inspect the decision methods', explore('models')),
        'Jev input before and after': ('Inspect this scheduler case', explore('transform', 'NS-b073aba91088')),
        'Results': ('Explore scores and individual failures', explore('results')),
        'Next experiment': ('Explore the next experiment', explore('next')),
    }
    # The first heading is displayed as the article's hero, with its original anchor retained.
    start = 3 if tokens and tokens[0].type == 'heading_open' and tokens[0].tag == 'h1' else 0
    article_parts = []
    segment = start
    for i in range(start, len(tokens)):
        token = tokens[i]
        if token.type == 'heading_close' and document == 'overview':
            label = tokens[i - 1].content
            if label in cues:
                article_parts.append(md.renderer.render(tokens[segment:i + 1], md.options, {}))
                label, href = cues[label]
                article_parts.append(f'<a class="inspect-link" href="{escape(href, quote=True)}">{escape(label)} <span aria-hidden="true">↗</span></a>')
                segment = i + 1
    article_parts.append(md.renderer.render(tokens[segment:], md.options, {}))
    article = ''.join(article_parts)
    # Table rendering stays under the Markdown parser; wrappers add local scrolling and inspection.
    article = article.replace('<table>', '<div class="reading-table"><div class="table-actions"><span class="scroll-hint" hidden>Scroll sideways to read all columns</span><button type="button" data-expand-table>Expand table</button></div><div class="table-scroll" tabindex="0" role="region" aria-label="Study comparison table"><table>')
    article = article.replace('</table>', '</table></div></div>')
    toc = ''.join(f'<a class="toc-{tag}" href="#{anchor}">{escape(label)}</a>' for tag, label, anchor in headings)
    sections = ''.join(f'<option value="{anchor}">{"  " if tag == "h3" else ""}{escape(label)}</option>' for tag, label, anchor in headings)
    minutes = max(1, math.ceil(len(re.findall(r'\b\w+\b', source)) / 220))
    download = '/study.md' if document == 'overview' else '/study.md?doc=' + document
    hero_anchor = tokens[0].attrGet('id') if start else 'section-study'
    return Template((Path(__file__).parent / 'web/study.html').read_text()).substitute(
        title=escape(title), back=escape(back, quote=True), article=article,
        toc=toc, sections=sections, minutes=minutes, hero_anchor=hero_anchor,
        download=escape(download, quote=True), filename=Path(DOCUMENTS[document]).name,
        kind='Study overview' if document == 'overview' else 'Study reference',
    ).encode()
