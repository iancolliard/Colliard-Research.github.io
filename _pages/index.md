---
layout: compress
---

{% include base_path %}

<!doctype html>
<html lang="{{ site.locale | slice: 0,2 }}" class="no-js"{% if site.site_theme == "dark" %} data-theme="dark"{% endif %}>
  <head>
    {% include head.html %}
    {% include head/custom.html %}
  </head>

  <body>

    {% include browser-upgrade.html %}
    {% include masthead.html %}

    {{ content }}

    <div class="page__footer">
      <footer>
        {% include footer/custom.html %}
        {% include footer.html %}
      </footer>
    </div>

    {% include scripts.html %}

  </body>
</html>
<ul>
{%- assign kids = site.pages
  | where_exp: "p", "p.path contains 'crystallography/'"
  | where_exp: "p", "p.url != '/crystallography/'"
  | sort: "title" -%}
{%- for p in kids -%}
  <li><a href="{{ p.url | relative_url }}">{{ p.title }}</a></li>
{%- endfor -%}
</ul>