---
layout: archive
title: "CV"
permalink: /cv/
author_profile: true
redirect_from:
  - /resume
---

{% include base_path %}

<h1>Publications</h1>

{% assign pubs = site.publications | sort: "date" | reverse %}
{% assign groups = pubs | group_by_exp: "p", "p.date | date: '%Y'" %}

{% for g in groups %}
  <h2>{{ g.name }}</h2>
  <ul>
    {% for post in g.items %}
      <li>
        <strong><a href="{{ post.url | relative_url }}">{{ post.title }}</a></strong><br>
        {% if venue %}
          <em>{{ venue }}</em>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
{% endfor %}
