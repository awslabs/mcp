---
id: "OPS11-BP04"
title: "Perform knowledge management"
pillar: "Operational Excellence"
risk_level: "HIGH"
capability: "How do you evolve operations?"
url: "https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_evolve_ops_knowledge_management.html"
description: "Knowledge management helps team members find the information to perform their job. In learning organizations, information is freely shared which empowers individuals. The information can be discovered or searched. Information is accurate and up to date. Mechanisms exist to create new information, update existing information, and archive outdated information. The most common example of a knowledge management platform is a content management system like a wiki."
area: ["Evolve", "Learn, share, and improve"]
relatedIds: ["OPS11-BP08"]
---

# OPS11-BP04 Perform knowledge management

Knowledge management helps team members find the information to perform their job. In learning organizations, information is freely shared which empowers individuals. The information can be discovered or searched. Information is accurate and up to date. Mechanisms exist to create new information, update existing information, and archive outdated information. The most common example of a knowledge management platform is a content management system like a wiki.

**Desired outcome:**

- Team members have access to timely, accurate information.
- Information is searchable.
- Mechanisms exist to add, update, and archive information.

**Common anti-patterns:**

- There is no centralized knowledge storage. Team members manage their own notes on their local machines.
- You have a self-hosted wiki but no mechanisms to manage information, resulting in outdated information.
- Someone identifies missing information but there’s no process to request adding it the team wiki. They add it themselves but they miss a key step, leading to an outage.

**Benefits of establishing this best practice:**

- Team members are empowered because information is shared freely.
- New team members are onboarded faster because documentation is up to date and searchable.
- Information is timely, accurate, and actionable.

**Level of risk exposed if this best practice
is not established:** High

## Implementation guidance

Knowledge management is an important facet of learning organizations. To begin, you need a central repository to store your knowledge (as a common example, a self-hosted wiki). You must develop processes for adding, updating, and archiving knowledge. Develop standards for what should be documented and let everyone contribute.

**Customer example**

AnyCompany Retail hosts an internal Wiki where all knowledge is stored. Team members are encouraged to add to the knowledge base as they go about their daily duties. On a quarterly basis, a cross-functional team evaluates which pages are least updated and determines if they should be archived or updated.

**Implementation steps**

- Start with identifying the content management system where knowledge will be stored. Get agreement from stakeholders across your organization.

If you don’t have an existing content management system, consider running a self-hosted wiki or using a version control repository as a starting point.

- Develop runbooks for adding, updating, and archiving information. Educate your team on these processes.
- Identify what knowledge should be stored in the content management system. Start with daily activities (runbooks and playbooks) that team members perform. Work with stakeholders to prioritize what knowledge is added.
- On a periodic basis, work with stakeholders to identify out-of-date information and archive it or bring it up to date.

**Level of effort for the implementation plan:** Medium. If you don’t have an existing content management system, you can set up a self-hosted wiki or a version-controlled document repository.

## Resources

**Related best practices:**

- [OPS11-BP08 Document and share lessons learned](./ops_evolve_ops_share_lessons_learned.html) - Knowledge management facilitates information sharing about lessons learned.

**Related documents:**

- [Atlassian - Knowledge Management](https://www.atlassian.com/itsm/knowledge-management)

**Related examples:**

- [DokuWiki](https://www.dokuwiki.org/dokuwiki)
- [Gollum](https://github.com/gollum/gollum)
- [MediaWiki](https://www.mediawiki.org/wiki/MediaWiki)
- [Wiki.js](https://github.com/Requarks/wiki)
