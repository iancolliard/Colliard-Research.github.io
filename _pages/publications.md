---
layout: archive
title: List of Publications
permalink: /publications/
author_profile: true
---

{% if site.author.googlescholar %}
  <div class="wordwrap">You can also find my articles on <a href="{{site.author.googlescholar}}">my Google Scholar profile</a>.</div>
{% endif %}

{% include base_path %}

*****
<h1>Publications</h1>

{%- comment -%}
Sort newest → oldest, build a global countdown, then group by year.
{%- endcomment -%}
{%- assign pubs = site.publications | sort:"date" | reverse -%}
{%- assign total = pubs | size -%}
{%- assign counter = total -%}
{%- assign groups = pubs | group_by_exp: "p", "p.date | date: '%Y'" -%}

{%- for g in groups -%}
  <h2>{{ g.name }}</h2>
  <ol reversed start="{{ counter }}">
    {%- for post in g.items -%}
      <li>
        <!-- Link to the publication page (safe for GitHub Pages baseurl) -->
        <a href="{{ post.url | relative_url }}"><strong>{{ post.title }}</strong></a>
        {%- if post.paperurl -%}
          {%- if post.paperurl contains '://' -%}
            · <a href="{{ post.paperurl }}" target="_blank" rel="noopener">PDF</a>
          {%- else -%}
            · <a href="{{ post.paperurl | relative_url }}">PDF</a>
          {%- endif -%}
        {%- endif -%}
        <br>
        {%- if post.journal -%}<em>{{ post.journal }}</em>{%- endif -%}
      </li>
    {%- endfor -%}
  </ol>
  {%- assign counter = counter | minus: g.items.size -%}
{%- endfor -%}

