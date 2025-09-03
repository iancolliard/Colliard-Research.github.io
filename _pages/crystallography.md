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

{%- assign pubs = site.publications | sort: "date" | reverse -%}
{%- assign total = pubs | size -%}
{%- assign counter = total -%}

{%- assign groups = pubs | group_by_exp: "p", "p.date | date: '%Y'" -%}
{%- for g in groups -%}
  <h2>{{ g.name }}</h2>
  <ol reversed start="{{ counter }}">
    {%- for post in g.items -%}
      <li>
        <strong><a href="{{ post.url | relative_url }}">{{ post.title }}</a></strong><br>
        {%- if post.journal -%}<em>{{ post.journal }}</em>{%- endif -%}
      </li>
    {%- endfor -%}
  </ol>
  {%- assign counter = counter | minus: g.items.size -%}
{%- endfor -%}

