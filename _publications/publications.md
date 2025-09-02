layout: archive
title: "Publications"
permalink: /publications/
author_profile: true
redirect_from:
  - /publications
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
        {% if post.journal %}
          <em>{{ post.journal }}</em>
        {% endif %}
      </li>
    {% endfor %}
  </ul>
{% endfor %}
