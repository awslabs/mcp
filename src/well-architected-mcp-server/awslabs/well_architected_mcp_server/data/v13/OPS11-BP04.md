---
id: "OPS11-BP04"
title: "Perform knowledge management"
framework: "WAF"
domain: "Operational Excellence"
capability: "How do you evolve operations?"
risk_level: "High"
effort: "Medium"
---

# OPS11-BP04 Perform knowledge management

## Desired Outcome
- Team members have access to timely, accurate information.
- Information is searchable.
- Mechanisms exist to add, update, and archive information.

## Anti-Patterns
- There is no centralized knowledge storage. Team members manage their own notes on their local machines.
- You have a self-hosted wiki but no mechanisms to manage information, resulting in outdated information.
- Someone identifies missing information but there’s no process to request adding it the team wiki. They add it themselves but they miss a key step, leading to an outage.

## Implementation Guidance
 Knowledge management is an important facet of learning organizations. To begin, you need a central repository to store your knowledge (as a common example, a self-hosted wiki). You must develop processes for adding, updating, and archiving knowledge. Develop standards for what should be documented and let everyone contribute.

 **Customer example**

 AnyCompany Retail hosts an internal Wiki where all knowledge is stored. Team members are encouraged to add to the knowledge base as they go about their daily duties. On a quarterly basis, a cross-functional team evaluates which pages are least updated and determines if they should be archived or updated.

## Implementation Steps
1.  Start with identifying the content management system where knowledge will be stored. Get agreement from stakeholders across your organization.

   1.  If you don’t have an existing content management system, consider running a self-hosted wiki or using a version control repository as a starting point.

1.  Develop runbooks for adding, updating, and archiving information. Educate your team on these processes.

1.  Identify what knowledge should be stored in the content management system. Start with daily activities (runbooks and playbooks) that team members perform. Work with stakeholders to prioritize what knowledge is added.

1.  On a periodic basis, work with stakeholders to identify out-of-date information and archive it or bring it up to date.

## Resources
### Related Best Practices
- [OPS11-BP08 Document and share lessons learned](ops_evolve_ops_share_lessons_learned.md) - Knowledge management facilitates information sharing about lessons learned.
### Related Documents
- [ Atlassian - Knowledge Management ](https://www.atlassian.com/itsm/knowledge-management)
### Related Examples
- [ DokuWiki ](https://www.dokuwiki.org/dokuwiki)
- [ Gollum ](https://github.com/gollum/gollum)
- [ MediaWiki ](https://www.mediawiki.org/wiki/MediaWiki)
- [ Wiki.js ](https://github.com/Requarks/wiki)
